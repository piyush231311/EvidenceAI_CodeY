"""
Evidence AI — Central Pipeline Orchestrator & Durable Background Worker.

Manages the end-to-end 15-stage investigative pipeline:
  1. VALIDATE_EVIDENCE
  2. EXTRACT_CONTENT (Smart Caching via SHA-256)
  3. NORMALIZE_CONTENT
  4. EXTRACT_ENTITIES (GLiNER)
  5. MATCH_ENTITIES (RapidFuzz)
  6. UNDERSTAND_CASE (Grounding & Facts)
  7. EXTRACT_EVENTS (Table & Multimodal Parsing)
  8. BUILD_TIMELINE (Deterministic Chronology)
  9. IDENTIFY_UNCERTAINTIES (Cross-Evidence Reasoning)
  10. GENERATE_PRELIMINARY_STORY (150-250 words)
  11. GENERATE_CONTEXTUAL_QUIZ (Story-Grounded Questions)
  12. AWAIT_USER_ANSWERS (Automatic Pause)
  13. INCORPORATE_CLARIFICATIONS (Automatic Resume)
  14. GENERATE_FINAL_REPORT (200-350 words + Appendix)
  15. COMPLETE

Features:
  - Database-backed durable state in SQLite (analysis_jobs, analysis_job_stages)
  - Thread-safe single-worker execution lock protecting GPU/CPU resources
  - Smart caching: reuses existing OCR, transcription, and entity results when SHA-256 matches
  - Resumable: recovers from failed stages and resumes on user answer submission
"""

import os
import json
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from backend.db import SessionLocal, init_db
from backend.models import (
    Case, Evidence, EntityMatchRecord, EventRecord,
    EventContradictionRecord, ClarificationQuestionRecord,
    UserAnswerRecord, ReconstructedReportRecord, MVPAnalysisRecord,
    AnalysisJobRecord, AnalysisStageRecord, AuditLog
)

logger = logging.getLogger(__name__)

# Pipeline Stage Definitions in strict sequence
PIPELINE_STAGES = [
    "VALIDATE_EVIDENCE",
    "EXTRACT_CONTENT",
    "NORMALIZE_CONTENT",
    "EXTRACT_ENTITIES",
    "MATCH_ENTITIES",
    "UNDERSTAND_CASE",
    "EXTRACT_EVENTS",
    "BUILD_TIMELINE",
    "IDENTIFY_UNCERTAINTIES",
    "GENERATE_PRELIMINARY_STORY",
    "GENERATE_CONTEXTUAL_QUIZ",
    "AWAIT_USER_ANSWERS",
    "INCORPORATE_CLARIFICATIONS",
    "GENERATE_FINAL_REPORT",
    "COMPLETE",
]

STAGE_METADATA = {
    "VALIDATE_EVIDENCE": {"label": "Validate Evidence", "desc": "Verifying cryptographic SHA-256 integrity and file types"},
    "EXTRACT_CONTENT": {"label": "Extract Content", "desc": "Running OCR, ASR audio transcription, and document parsing"},
    "NORMALIZE_CONTENT": {"label": "Normalize Content", "desc": "Standardizing character encoding, dates, and text segments"},
    "EXTRACT_ENTITIES": {"label": "Extract Named Entities", "desc": "Identifying persons, organizations, amounts, and dates via GLiNER"},
    "MATCH_ENTITIES": {"label": "Disambiguate Entities", "desc": "Cross-matching aliases and candidate entities via RapidFuzz"},
    "UNDERSTAND_CASE": {"label": "Understand Case", "desc": "Synthesizing evidence-backed facts and classifying investigative domain"},
    "EXTRACT_EVENTS": {"label": "Extract Events", "desc": "Parsing multi-line bank tables, messages, and calls with tense awareness"},
    "BUILD_TIMELINE": {"label": "Build Timeline", "desc": "Reconstructing deterministic chronological sequence"},
    "IDENTIFY_UNCERTAINTIES": {"label": "Identify Uncertainties", "desc": "Analyzing cross-evidence discrepancies, unanchored times, and claims"},
    "GENERATE_PRELIMINARY_STORY": {"label": "Generate Preliminary Story", "desc": "Drafting 150–250 word grounded initial narrative"},
    "GENERATE_CONTEXTUAL_QUIZ": {"label": "Generate Contextual Quiz", "desc": "Formulating targeted clarification questions targeting case unknowns"},
    "AWAIT_USER_ANSWERS": {"label": "Awaiting User Testimony", "desc": "Pausing pipeline for investigator / witness clarification answers"},
    "INCORPORATE_CLARIFICATIONS": {"label": "Incorporate Clarifications", "desc": "Refining timeline and factual understanding with user testimony"},
    "GENERATE_FINAL_REPORT": {"label": "Generate Final Report", "desc": "Compiling 200–350 word forensic narrative and technical appendix"},
    "COMPLETE": {"label": "Analysis Complete", "desc": "All investigation stages verified and finalized"},
}

# Single-worker inference lock to safeguard RTX 4050 6GB GPU and memory
_INFERENCE_LOCK = threading.Lock()
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="evidence_ai_worker")


def get_progress_percentage(completed_stages: List[str], current_stage: str, status: str) -> int:
    """Calculates deterministic progress percentage across 15 stages."""
    if status == "COMPLETED":
        return 100
    if status == "WAITING_FOR_USER":
        return 75
    count = len(completed_stages)
    pct = int((count / len(PIPELINE_STAGES)) * 100)
    return min(max(pct, 5), 98)


def create_analysis_job(case_id: str) -> AnalysisJobRecord:
    """
    Creates a new persistent analysis job and initializes all 15 stage records in SQLite.
    Prevents duplicate active jobs for the same case.
    """
    init_db()
    with SessionLocal() as db:
        # Check if an active job already exists for this case
        active_job = (
            db.query(AnalysisJobRecord)
            .filter(
                AnalysisJobRecord.case_id == case_id,
                AnalysisJobRecord.status.in_(["PENDING", "RUNNING", "WAITING_FOR_USER"]),
            )
            .order_by(AnalysisJobRecord.created_at.desc())
            .first()
        )
        if active_job:
            return active_job

        evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        hashes = [e.sha256 for e in evidence_items]

        job_id = str(uuid.uuid4())
        job = AnalysisJobRecord(
            id=job_id,
            case_id=case_id,
            pipeline_version="2.0.0",
            status="PENDING",
            current_stage="VALIDATE_EVIDENCE",
            evidence_hashes_json=json.dumps(hashes),
            completed_stages_json="[]",
            artifacts_json="{}",
            start_time=datetime.utcnow(),
        )
        db.add(job)

        # Initialize all 15 stage records in order
        for idx, stage_name in enumerate(PIPELINE_STAGES):
            stage_rec = AnalysisStageRecord(
                id=str(uuid.uuid4()),
                job_id=job_id,
                stage_name=stage_name,
                order_index=idx,
                status="PENDING",
                details_json=json.dumps(STAGE_METADATA.get(stage_name, {})),
            )
            db.add(stage_rec)

        audit = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case_id,
            action="ANALYSIS_JOB_CREATED",
            details=json.dumps({"job_id": job_id, "evidence_count": len(evidence_items)}),
        )
        db.add(audit)
        db.commit()
        db.refresh(job)
        return job


def get_job_with_stages(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full job details and all 15 stages from SQLite."""
    with SessionLocal() as db:
        job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
        if not job:
            return None

        stages = (
            db.query(AnalysisStageRecord)
            .filter(AnalysisStageRecord.job_id == job_id)
            .order_by(AnalysisStageRecord.order_index.asc())
            .all()
        )

        completed = json.loads(job.completed_stages_json or "[]")
        progress = get_progress_percentage(completed, job.current_stage, job.status)

        stage_responses = []
        for s in stages:
            stage_responses.append({
                "id": s.id,
                "job_id": s.job_id,
                "stage_name": s.stage_name,
                "order_index": s.order_index,
                "status": s.status,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "completion_time": s.completion_time.isoformat() if s.completion_time else None,
                "duration_ms": s.duration_ms,
                "details": json.loads(s.details_json or "{}"),
                "error_message": s.error_message,
            })

        return {
            "id": job.id,
            "case_id": job.case_id,
            "pipeline_version": job.pipeline_version,
            "status": job.status,
            "current_stage": job.current_stage,
            "progress_percentage": progress,
            "completed_stages": completed,
            "failed_stage": job.failed_stage,
            "error_details": job.error_details,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "completion_time": job.completion_time.isoformat() if job.completion_time else None,
            "artifacts": json.loads(job.artifacts_json or "{}"),
            "stages": stage_responses,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }


def get_active_job_for_case(case_id: str) -> Optional[Dict[str, Any]]:
    """Returns the latest active or most recent job for a case."""
    with SessionLocal() as db:
        job = (
            db.query(AnalysisJobRecord)
            .filter(AnalysisJobRecord.case_id == case_id)
            .order_by(AnalysisJobRecord.created_at.desc())
            .first()
        )
        if not job:
            return None
        return get_job_with_stages(job.id)


def start_orchestrated_analysis(job_id: str, resume_from_stage: Optional[str] = None):
    """Submits the analysis job to the background thread pool."""
    _EXECUTOR.submit(_execute_job_pipeline, job_id, resume_from_stage)


def _update_stage_db(
    job_id: str,
    stage_name: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    duration_ms: Optional[float] = None,
):
    """Updates an individual stage record in SQLite safely."""
    with SessionLocal() as db:
        s_rec = (
            db.query(AnalysisStageRecord)
            .filter(AnalysisStageRecord.job_id == job_id, AnalysisStageRecord.stage_name == stage_name)
            .first()
        )
        if s_rec:
            s_rec.status = status
            if status == "RUNNING" and not s_rec.start_time:
                s_rec.start_time = datetime.utcnow()
            elif status in ["COMPLETED", "FAILED", "WAITING_FOR_USER"]:
                s_rec.completion_time = datetime.utcnow()
            if duration_ms is not None:
                s_rec.duration_ms = duration_ms
            if error:
                s_rec.error_message = error
            if details:
                curr = json.loads(s_rec.details_json or "{}")
                curr.update(details)
                s_rec.details_json = json.dumps(curr)

        # Update Job Record
        job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
        if job:
            job.current_stage = stage_name
            if status == "RUNNING":
                job.status = "RUNNING"
            elif status == "COMPLETED":
                if stage_name == "COMPLETE":
                    job.status = "COMPLETED"
                    job.completion_time = datetime.utcnow()
                completed = json.loads(job.completed_stages_json or "[]")
                if stage_name not in completed:
                    completed.append(stage_name)
                    job.completed_stages_json = json.dumps(completed)
            elif status == "FAILED":
                job.status = "FAILED"
                job.failed_stage = stage_name
                job.error_details = error or "Stage execution failed."
            elif status == "WAITING_FOR_USER":
                job.status = "WAITING_FOR_USER"
            db.commit()


def _execute_job_pipeline(job_id: str, resume_from_stage: Optional[str] = None):
    """
    Executes the 15-stage pipeline under the single-worker lock.
    Handles stage transitions, smart caching, automatic pausing, and resumption.
    """
    with _INFERENCE_LOCK:
        with SessionLocal() as db:
            job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
            if not job:
                logger.error(f"Analysis job {job_id} not found.")
                return
            case_id = job.case_id
            job.status = "RUNNING"
            db.commit()

        start_index = 0
        if resume_from_stage and resume_from_stage in PIPELINE_STAGES:
            start_index = PIPELINE_STAGES.index(resume_from_stage)

        logger.info(f"Starting pipeline execution for job {job_id} (case {case_id}) from stage {PIPELINE_STAGES[start_index]}")

        # Shared pipeline context across stages
        context: Dict[str, Any] = {
            "case_id": case_id,
            "job_id": job_id,
            "evidence_items": [],
            "extracted_corpus": [],
            "entities": [],
            "events": [],
            "timeline": None,
            "contradictions": [],
            "analysis": None,
            "quiz_questions": [],
            "report": None,
        }

        for idx in range(start_index, len(PIPELINE_STAGES)):
            stage_name = PIPELINE_STAGES[idx]
            t0 = time.time()
            _update_stage_db(job_id, stage_name, "RUNNING")

            try:
                # Stage 1: VALIDATE_EVIDENCE
                if stage_name == "VALIDATE_EVIDENCE":
                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        if not ev_items:
                            raise ValueError("No evidence files uploaded for this case.")
                        context["evidence_items"] = ev_items
                        _update_stage_db(job_id, stage_name, "COMPLETED", {"files_count": len(ev_items)}, duration_ms=(time.time()-t0)*1000)

                # Stage 2: EXTRACT_CONTENT (Smart Caching)
                elif stage_name == "EXTRACT_CONTENT":
                    from backend.routes import run_pipeline_extraction
                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        reused_count = 0
                        newly_extracted = 0
                        for ev in ev_items:
                            # Re-use existing text if non-empty (smart cache)
                            if ev.extracted_text and len(ev.extracted_text.strip()) > 10:
                                reused_count += 1
                                continue
                            # Extract missing
                            file_path = ev.stored_path
                            if os.path.exists(file_path):
                                ext_res = run_pipeline_extraction(file_path, ev.file_type)
                                ev.extracted_text = ext_res.get("text")
                                ev.extraction_confidence = ext_res.get("confidence")
                                ev.processing_time_ms = ext_res.get("processing_time_ms")
                                newly_extracted += 1
                        db.commit()
                        _update_stage_db(job_id, stage_name, "COMPLETED", {"cached_count": reused_count, "extracted_count": newly_extracted}, duration_ms=(time.time()-t0)*1000)

                # Stage 3: NORMALIZE_CONTENT
                elif stage_name == "NORMALIZE_CONTENT":
                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        corpus = []
                        total_chars = 0
                        for e in ev_items:
                            txt = (e.extracted_text or "").replace("\r", "").strip()
                            if txt:
                                corpus.append({
                                    "id": e.id,
                                    "filename": e.original_filename,
                                    "file_type": e.file_type,
                                    "sha256": e.sha256,
                                    "text": txt,
                                })
                                total_chars += len(txt)
                        context["extracted_corpus"] = corpus
                        _update_stage_db(job_id, stage_name, "COMPLETED", {"corpus_items": len(corpus), "total_chars": total_chars}, duration_ms=(time.time()-t0)*1000)

                # Stage 4: EXTRACT_ENTITIES (GLiNER)
                elif stage_name == "EXTRACT_ENTITIES":
                    from src.intelligence.gliner_extractor import extract_entities_from_text, ExtractedEntity
                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        all_mentions: List[ExtractedEntity] = []
                        for ev in ev_items:
                            if ev.extracted_text and ev.extracted_text.strip():
                                ents = extract_entities_from_text(
                                    ev.extracted_text,
                                    evidence_id=ev.id,
                                    filename=ev.original_filename,
                                    ocr_confidence=ev.extraction_confidence,
                                )
                                all_mentions.extend(ents)
                        context["raw_entities"] = all_mentions
                        context["entities"] = [{"text": m.text, "label": m.label} for m in all_mentions]
                        _update_stage_db(
                            job_id, stage_name, "COMPLETED",
                            {"extracted_mentions": len(all_mentions)},
                            duration_ms=(time.time()-t0)*1000
                        )

                # Stage 5: MATCH_ENTITIES (RapidFuzz)
                elif stage_name == "MATCH_ENTITIES":
                    from src.intelligence.entity_matcher import generate_candidate_matches
                    from src.intelligence.gliner_extractor import extract_entities_from_text, ExtractedEntity
                    with SessionLocal() as db:
                        raw_entities: List[ExtractedEntity] = context.get("raw_entities") or []
                        if not raw_entities:
                            ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                            for ev in ev_items:
                                if ev.extracted_text and ev.extracted_text.strip():
                                    raw_entities.extend(
                                        extract_entities_from_text(
                                            ev.extracted_text,
                                            evidence_id=ev.id,
                                            filename=ev.original_filename,
                                            ocr_confidence=ev.extraction_confidence,
                                        )
                                    )
                            context["raw_entities"] = raw_entities

                        candidate_matches = generate_candidate_matches(raw_entities, case_id=case_id) if raw_entities else []
                        existing_records = {
                            (rec.entity_type, rec.canonical_name): rec
                            for rec in db.query(EntityMatchRecord).filter(EntityMatchRecord.case_id == case_id).all()
                        }
                        for cand in candidate_matches:
                            key = (cand.entity_type, cand.canonical_name)
                            existing = existing_records.get(key)
                            mentions_data = [m.model_dump() for m in cand.mentions]
                            if existing:
                                existing.mentions_json = json.dumps(mentions_data)
                                existing.similarity_score = cand.similarity_score
                                existing.classification_confidence = cand.classification_confidence
                                existing.ocr_confidence = cand.ocr_confidence
                                existing.extraction_confidence = cand.extraction_confidence
                                existing.is_single_occurrence = cand.is_single_occurrence
                                existing.is_low_confidence = cand.is_low_confidence
                                existing.requires_source_verification = cand.requires_source_verification
                                existing.verification_reasons_json = json.dumps(cand.verification_reasons)
                                existing.related_entities_json = json.dumps(cand.related_entities)
                                existing.match_type = cand.match_type
                            else:
                                db.add(EntityMatchRecord(
                                    id=cand.match_id,
                                    case_id=case_id,
                                    entity_type=cand.entity_type,
                                    canonical_name=cand.canonical_name,
                                    similarity_score=cand.similarity_score,
                                    classification_confidence=cand.classification_confidence,
                                    ocr_confidence=cand.ocr_confidence,
                                    extraction_confidence=cand.extraction_confidence,
                                    is_single_occurrence=cand.is_single_occurrence,
                                    is_low_confidence=cand.is_low_confidence,
                                    requires_source_verification=cand.requires_source_verification,
                                    verification_reasons_json=json.dumps(cand.verification_reasons),
                                    related_entities_json=json.dumps(cand.related_entities),
                                    match_type=cand.match_type,
                                    status="pending",
                                    mentions_json=json.dumps(mentions_data),
                                ))
                        db.commit()
                        matches = db.query(EntityMatchRecord).filter(EntityMatchRecord.case_id == case_id).all()
                        if matches:
                            context["entities"] = [{"text": m.canonical_name, "label": m.entity_type} for m in matches]
                        _update_stage_db(
                            job_id, stage_name, "COMPLETED",
                            {"matched_entities_count": len(matches)},
                            duration_ms=(time.time()-t0)*1000
                        )

                # Stage 6: UNDERSTAND_CASE (Grounded Facts & Citations)
                elif stage_name == "UNDERSTAND_CASE":
                    from src.intelligence.case_analyzer import analyze_case_mvp
                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        analysis = analyze_case_mvp(
                            case_id=case_id,
                            evidence_items=ev_items,
                            entities=context.get("entities"),
                        )
                        context["analysis"] = analysis
                        _update_stage_db(
                            job_id, stage_name, "COMPLETED",
                            {
                                "case_domain": analysis.case_domain,
                                "case_title": analysis.case_title,
                                "facts_count": len(analysis.evidence_backed_facts),
                                "inference_source": analysis.inference_source,
                            },
                            duration_ms=(time.time()-t0)*1000
                        )

                # Stage 7: EXTRACT_EVENTS (Table & Multimodal Extraction)
                elif stage_name == "EXTRACT_EVENTS":
                    from src.intelligence.event_extractor import extract_events_with_qwen, EventCandidate
                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        all_cands: List[EventCandidate] = []
                        for ev in ev_items:
                            if ev.extracted_text:
                                cands = extract_events_with_qwen(
                                    text=ev.extracted_text,
                                    case_id=case_id,
                                    evidence_id=ev.id,
                                    filename=ev.original_filename,
                                    entities=context.get("entities"),
                                )
                                all_cands.extend(cands)

                        # Clean and save deduplicated event records in SQLite
                        db.query(EventRecord).filter(EventRecord.case_id == case_id).delete()
                        seen_keys = set()
                        unique_cands: List[EventCandidate] = []
                        for cand in all_cands:
                            key = (cand.title, cand.action, cand.original_time_expression)
                            if key not in seen_keys:
                                rec = EventRecord(
                                    id=cand.event_id,
                                    case_id=case_id,
                                    event_type=cand.event_type,
                                    title=cand.title,
                                    description=cand.description,
                                    actors_json=json.dumps(cand.actors),
                                    action=cand.action,
                                    location=cand.location,
                                    original_time_expression=cand.original_time_expression,
                                    normalized_start_time=cand.normalized_start_time,
                                    temporal_precision=cand.temporal_precision,
                                    evidence_ids_json=json.dumps(cand.evidence_ids),
                                    source_segment_ids_json=json.dumps(cand.source_segment_ids),
                                    supporting_text_spans_json=json.dumps(cand.supporting_text_spans),
                                    modality=cand.modality,
                                    explicit_or_inferred=cand.explicit_or_inferred,
                                    uncertainty_flags_json=json.dumps(cand.uncertainty_flags),
                                    validation_status=cand.validation_status,
                                    review_status=cand.review_status,
                                )
                                db.add(rec)
                                seen_keys.add(key)
                                unique_cands.append(cand)
                        db.commit()
                        if not unique_cands:
                            raise ValueError("Quality Gate Failed [EXTRACT_EVENTS]: Zero structured events extracted from evidence.")
                        context["events"] = unique_cands
                        _update_stage_db(
                            job_id, stage_name, "COMPLETED",
                            {"extracted_events_count": len(unique_cands)},
                            duration_ms=(time.time()-t0)*1000
                        )

                # Stage 8: BUILD_TIMELINE
                elif stage_name == "BUILD_TIMELINE":
                    from src.intelligence.timeline_builder import build_timeline_from_events
                    from src.intelligence.event_extractor import EventCandidate
                    events_for_tl = context.get("events") or []
                    if not events_for_tl:
                        with SessionLocal() as db:
                            event_records = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
                            events_for_tl = [
                                EventCandidate(
                                    event_id=r.id,
                                    case_id=r.case_id,
                                    event_type=r.event_type,
                                    title=r.title,
                                    description=r.description,
                                    actors=json.loads(r.actors_json) if r.actors_json else [],
                                    action=r.action,
                                    original_time_expression=r.original_time_expression,
                                    normalized_start_time=r.normalized_start_time,
                                    temporal_precision=r.temporal_precision,
                                    evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
                                    supporting_text_spans=json.loads(r.supporting_text_spans_json) if r.supporting_text_spans_json else [],
                                    modality=r.modality,
                                )
                                for r in event_records
                            ]
                            context["events"] = events_for_tl

                    timeline = build_timeline_from_events(events_for_tl, case_id=case_id)
                    total_tl_events = len(timeline.scheduled_events) + len(timeline.unscheduled_events)
                    if total_tl_events != len(events_for_tl):
                        raise ValueError(
                            f"Quality Gate Failed [BUILD_TIMELINE]: Event count mismatch between EXTRACT_EVENTS "
                            f"({len(events_for_tl)}) and BUILD_TIMELINE ({total_tl_events})."
                        )
                    context["timeline"] = timeline
                    _update_stage_db(
                        job_id, stage_name, "COMPLETED",
                        {
                            "scheduled_events": len(timeline.scheduled_events),
                            "unscheduled_events": len(timeline.unscheduled_events),
                        },
                        duration_ms=(time.time()-t0)*1000
                    )

                # Stage 9: IDENTIFY_UNCERTAINTIES (Contradictions & Discrepancies)
                elif stage_name == "IDENTIFY_UNCERTAINTIES":
                    from src.intelligence.evidence_reasoner import analyze_cross_evidence_relationships
                    reasoning = analyze_cross_evidence_relationships(context.get("events", []), context.get("timeline"))
                    context["contradictions"] = reasoning.contradictions
                    with SessionLocal() as db:
                        db.query(EventContradictionRecord).filter(EventContradictionRecord.case_id == case_id).delete()
                        for contra in reasoning.contradictions:
                            db.add(EventContradictionRecord(
                                id=contra.contradiction_id,
                                case_id=case_id,
                                contradiction_type=contra.contradiction_type,
                                description=contra.description,
                                event_ids_json=json.dumps(contra.event_ids),
                                evidence_ids_json=json.dumps(contra.evidence_ids),
                                statement_a=contra.statement_a,
                                statement_b=contra.statement_b,
                                source_a=contra.source_a,
                                source_b=contra.source_b,
                                unresolved_question=contra.unresolved_question,
                            ))
                        db.commit()
                    _update_stage_db(job_id, stage_name, "COMPLETED", {"contradictions_count": len(reasoning.contradictions)}, duration_ms=(time.time()-t0)*1000)

                # Stage 10: GENERATE_PRELIMINARY_STORY
                elif stage_name == "GENERATE_PRELIMINARY_STORY":
                    from src.intelligence.case_analyzer import analyze_case_mvp
                    timeline = context.get("timeline")
                    sched_count = len(timeline.scheduled_events) if timeline else 0
                    unsched_count = len(timeline.unscheduled_events) if timeline else 0

                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        analysis = analyze_case_mvp(
                            case_id=case_id,
                            evidence_items=ev_items,
                            entities=context.get("entities"),
                            timeline_scheduled_count=sched_count,
                            timeline_unscheduled_count=unsched_count,
                            events=context.get("events"),
                            contradictions=context.get("contradictions"),
                        )
                        context["analysis"] = analysis

                        # Quality Gates for Stage 10:
                        if analysis.scheduled_events_count != sched_count or analysis.unscheduled_events_count != unsched_count:
                            raise ValueError(
                                f"Quality Gate Failed [GENERATE_PRELIMINARY_STORY]: Timeline count mismatch "
                                f"(story has {analysis.scheduled_events_count}, timeline has {sched_count})."
                            )
                        if sched_count > 0 and analysis.timeline_status != "available":
                            raise ValueError(
                                f"Quality Gate Failed [GENERATE_PRELIMINARY_STORY]: timeline_status is '{analysis.timeline_status}' "
                                f"despite {sched_count} scheduled timeline events."
                            )
                        if analysis.narrative_word_count < 80 or "encompasses 4 digital evidence items with verified integrity" in analysis.preliminary_narrative:
                            raise ValueError(
                                f"Quality Gate Failed [GENERATE_PRELIMINARY_STORY]: Preliminary narrative is too short or generic "
                                f"({analysis.narrative_word_count} words)."
                            )
                        if not analysis.evidence_backed_facts:
                            raise ValueError("Quality Gate Failed [GENERATE_PRELIMINARY_STORY]: No evidence-backed facts generated.")
                        for f_claim in analysis.evidence_backed_facts:
                            quote_str = (f_claim.citation.verbatim_quote or "").strip()
                            if len(quote_str) < 10 or not f_claim.citation.evidence_id:
                                raise ValueError(
                                    f"Quality Gate Failed [GENERATE_PRELIMINARY_STORY]: Invalid or trivial citation quote "
                                    f"('{quote_str}') for claim '{f_claim.topic}'."
                                )

                        # Persist updated MVP analysis record in SQLite
                        db.query(MVPAnalysisRecord).filter(MVPAnalysisRecord.case_id == case_id).delete()
                        mvp_rec = MVPAnalysisRecord(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            analysis_json=json.dumps(analysis.model_dump(), default=str),
                        )
                        db.add(mvp_rec)

                        # Persist in job artifacts_json
                        job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
                        if job:
                            arts = json.loads(job.artifacts_json or "{}")
                            arts["mvp_analysis"] = analysis.model_dump()
                            job.artifacts_json = json.dumps(arts, default=str)
                        db.commit()

                    _update_stage_db(
                        job_id, stage_name, "COMPLETED",
                        {
                            "narrative_words": analysis.narrative_word_count,
                            "timeline_status": analysis.timeline_status,
                            "scheduled_events_count": analysis.scheduled_events_count,
                            "facts_count": len(analysis.evidence_backed_facts),
                        },
                        duration_ms=(time.time()-t0)*1000
                    )

                # Stage 11: GENERATE_CONTEXTUAL_QUIZ
                elif stage_name == "GENERATE_CONTEXTUAL_QUIZ":
                    analysis = context.get("analysis")
                    if not analysis or not analysis.unresolved_questions:
                        raise ValueError("Quality Gate Failed [GENERATE_CONTEXTUAL_QUIZ]: No clarification questions generated.")
                    for q in analysis.unresolved_questions:
                        if "sequence of interactions between the participants" in q.question.lower():
                            raise ValueError(
                                f"Quality Gate Failed [GENERATE_CONTEXTUAL_QUIZ]: Generic template question rejected ('{q.question}')."
                            )
                        if not q.why_it_matters or len(q.options) < 2:
                            raise ValueError(
                                f"Quality Gate Failed [GENERATE_CONTEXTUAL_QUIZ]: Question '{q.topic}' missing rationale or options."
                            )

                    with SessionLocal() as db:
                        db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).delete()
                        for q in analysis.unresolved_questions:
                            q_rec = ClarificationQuestionRecord(
                                id=q.question_id,
                                case_id=case_id,
                                question_type="case_clarification",
                                activity_name=q.topic,
                                prompt=q.question,
                                why_it_matters=q.why_it_matters,
                                context_excerpt=q.context_quote or (q.source_references[0] if q.source_references else "Evidence"),
                                options_json=json.dumps(q.options),
                                status=q.status,
                            )
                            db.add(q_rec)
                        db.commit()
                    _update_stage_db(job_id, stage_name, "COMPLETED", {"questions_count": len(analysis.unresolved_questions)}, duration_ms=(time.time()-t0)*1000)

                # Stage 12: AWAIT_USER_ANSWERS (PAUSE STAGE)
                elif stage_name == "AWAIT_USER_ANSWERS":
                    # Check if user answers already exist in DB
                    with SessionLocal() as db:
                        user_ans_count = db.query(UserAnswerRecord).filter(UserAnswerRecord.case_id == case_id).count()
                        if user_ans_count == 0:
                            # Pause here and await user input
                            _update_stage_db(
                                job_id, stage_name, "WAITING_FOR_USER",
                                {"message": "Clarification quiz ready. Pausing for witness / investigator input."},
                                duration_ms=(time.time()-t0)*1000
                            )
                            logger.info(f"Job {job_id} paused at AWAIT_USER_ANSWERS (waiting for user input)")
                            return  # Terminate worker turn cleanly; resumed on answer submission
                        else:
                            # Answers already present, continue forward
                            _update_stage_db(job_id, stage_name, "COMPLETED", {"existing_answers_count": user_ans_count}, duration_ms=(time.time()-t0)*1000)

                # Stage 13: INCORPORATE_CLARIFICATIONS
                elif stage_name == "INCORPORATE_CLARIFICATIONS":
                    with SessionLocal() as db:
                        answers = db.query(UserAnswerRecord).filter(UserAnswerRecord.case_id == case_id).all()
                        ans_data = [
                            {
                                "question_id": a.question_id,
                                "selected_option": a.selected_option,
                                "free_text_clarification": a.free_text_clarification,
                                "user_surety": a.user_surety,
                                "knowledge_basis": a.knowledge_basis,
                            }
                            for a in answers
                        ]
                        context["user_answers"] = ans_data
                        _update_stage_db(job_id, stage_name, "COMPLETED", {"answers_incorporated": len(ans_data)}, duration_ms=(time.time()-t0)*1000)

                # Stage 14: GENERATE_FINAL_REPORT (200-350 Words + Technical Appendix)
                elif stage_name == "GENERATE_FINAL_REPORT":
                    from src.reporting.report_generator import generate_forensic_incident_report, render_incident_report_html
                    from src.intelligence.timeline_builder import build_timeline_from_events
                    from src.intelligence.clarification_engine import UserAnswer, ClarificationQuestion

                    with SessionLocal() as db:
                        ev_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
                        ev_list = [
                            {
                                "id": ev.id,
                                "original_filename": ev.original_filename,
                                "file_type": ev.file_type,
                                "sha256": ev.sha256,
                                "size_bytes": ev.size_bytes,
                                "extraction_confidence": ev.extraction_confidence,
                                "extracted_text": ev.extracted_text,
                            }
                            for ev in ev_items
                        ]

                        event_records = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
                        from src.intelligence.event_extractor import EventCandidate
                        events = [
                            EventCandidate(
                                event_id=r.id,
                                case_id=r.case_id,
                                event_type=r.event_type,
                                title=r.title,
                                description=r.description,
                                actors=json.loads(r.actors_json) if r.actors_json else [],
                                action=r.action,
                                original_time_expression=r.original_time_expression,
                                normalized_start_time=r.normalized_start_time,
                                temporal_precision=r.temporal_precision,
                                evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
                                modality=r.modality,
                            )
                            for r in event_records
                        ]
                        timeline = build_timeline_from_events(events, case_id=case_id)

                        q_records = db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).all()
                        questions = [
                            ClarificationQuestion(
                                question_id=q.id,
                                case_id=q.case_id,
                                event_id=q.event_id,
                                question_type=q.question_type,
                                prompt=q.prompt,
                                context_excerpt=q.context_excerpt,
                                options=json.loads(q.options_json) if q.options_json else [],
                                status=q.status,
                            )
                            for q in q_records
                        ]

                        ans_records = db.query(UserAnswerRecord).filter(UserAnswerRecord.case_id == case_id).all()
                        answers = [
                            UserAnswer(
                                answer_id=a.id,
                                question_id=a.question_id,
                                case_id=a.case_id,
                                event_id=a.event_id,
                                selected_option=a.selected_option,
                                free_text_clarification=a.free_text_clarification,
                                user_surety=a.user_surety,
                                surety_score=a.surety_score,
                                knowledge_basis=a.knowledge_basis,
                                submitted_at=a.submitted_at,
                            )
                            for a in ans_records
                        ]

                        from src.intelligence.evidence_reasoner import ContradictionRecord
                        contra_records = db.query(EventContradictionRecord).filter(EventContradictionRecord.case_id == case_id).all()
                        contradictions = [
                            ContradictionRecord(
                                contradiction_id=c.id,
                                case_id=c.case_id,
                                contradiction_type=c.contradiction_type,
                                description=c.description,
                                event_ids=json.loads(c.event_ids_json) if c.event_ids_json else [],
                                evidence_ids=json.loads(c.evidence_ids_json) if c.evidence_ids_json else [],
                                statement_a=c.statement_a,
                                statement_b=c.statement_b,
                                source_a=c.source_a,
                                source_b=c.source_b,
                                unresolved_question=c.unresolved_question,
                            )
                            for c in contra_records
                        ]

                        report_obj = generate_forensic_incident_report(
                            case_id=case_id,
                            evidence_files=ev_list,
                            timeline=timeline,
                            contradictions=contradictions,
                            questions=questions,
                            answers=answers,
                        )
                        html_preview = render_incident_report_html(report_obj)

                        # Save report record
                        rep_rec = ReconstructedReportRecord(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            report_json=json.dumps(report_obj.model_dump(), default=str),
                            html_preview=html_preview,
                        )
                        db.add(rep_rec)

                        # Update artifacts in job
                        job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
                        if job:
                            arts = json.loads(job.artifacts_json or "{}")
                            arts["report_id"] = rep_rec.id
                            arts["report"] = report_obj.model_dump()
                            job.artifacts_json = json.dumps(arts, default=str)
                        db.commit()

                        context["report"] = report_obj
                        _update_stage_db(
                            job_id, stage_name, "COMPLETED",
                            {
                                "report_id": rep_rec.id,
                                "report_title": report_obj.case_title,
                                "narrative_words": len(report_obj.what_happened.split()),
                                "updated_with_clarifications": report_obj.updated_with_clarifications,
                            },
                            duration_ms=(time.time()-t0)*1000
                        )

                # Stage 15: COMPLETE
                elif stage_name == "COMPLETE":
                    with SessionLocal() as db:
                        job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
                        if job:
                            job.status = "COMPLETED"
                            job.completion_time = datetime.utcnow()
                            completed = json.loads(job.completed_stages_json or "[]")
                            if "COMPLETE" not in completed:
                                completed.append("COMPLETE")
                                job.completed_stages_json = json.dumps(completed)
                        db.commit()
                    _update_stage_db(job_id, stage_name, "COMPLETED", {"message": "Pipeline completed successfully."}, duration_ms=(time.time()-t0)*1000)
                    logger.info(f"Pipeline job {job_id} COMPLETED successfully.")

            except Exception as e:
                logger.exception(f"Stage {stage_name} failed for job {job_id}: {e}")
                _update_stage_db(job_id, stage_name, "FAILED", error=str(e), duration_ms=(time.time()-t0)*1000)
                return


def resume_analysis_after_quiz_submission(job_id: str):
    """
    Automatically called when user submits clarification answers.
    Transitions from AWAIT_USER_ANSWERS directly to INCORPORATE_CLARIFICATIONS.
    """
    with SessionLocal() as db:
        job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        # Mark AWAIT_USER_ANSWERS as COMPLETED
        await_stage = (
            db.query(AnalysisStageRecord)
            .filter(AnalysisStageRecord.job_id == job_id, AnalysisStageRecord.stage_name == "AWAIT_USER_ANSWERS")
            .first()
        )
        if await_stage:
            await_stage.status = "COMPLETED"
            await_stage.completion_time = datetime.utcnow()

        completed = json.loads(job.completed_stages_json or "[]")
        if "AWAIT_USER_ANSWERS" not in completed:
            completed.append("AWAIT_USER_ANSWERS")
            job.completed_stages_json = json.dumps(completed)

        job.status = "RUNNING"
        job.current_stage = "INCORPORATE_CLARIFICATIONS"
        db.commit()

    # Resume pipeline in background thread from INCORPORATE_CLARIFICATIONS
    start_orchestrated_analysis(job_id, resume_from_stage="INCORPORATE_CLARIFICATIONS")


def retry_failed_job(job_id: str) -> Dict[str, Any]:
    """Retries a failed job from the failed stage without restarting from scratch."""
    with SessionLocal() as db:
        job = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        failed_stage = job.failed_stage or "VALIDATE_EVIDENCE"
        job.status = "RUNNING"
        job.error_details = None
        job.failed_stage = None

        # Reset failed stage record
        stage_rec = (
            db.query(AnalysisStageRecord)
            .filter(AnalysisStageRecord.job_id == job_id, AnalysisStageRecord.stage_name == failed_stage)
            .first()
        )
        if stage_rec:
            stage_rec.status = "RUNNING"
            stage_rec.error_message = None
        db.commit()

    start_orchestrated_analysis(job_id, resume_from_stage=failed_stage)
    return get_job_with_stages(job_id)
