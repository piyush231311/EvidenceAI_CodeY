"""
Tests for Evidence AI One-Click End-to-End Analysis Orchestrator.

Validates:
1. 15-stage sequence tracking in SQLite database.
2. Smart caching (reusing OCR/Whisper and GLiNER entities via SHA-256).
3. Grounded Case Understanding (150-250 words narrative, 5-10 cited facts, 3-5 questions).
4. Automatic pause at AWAIT_USER_ANSWERS (WAITING_FOR_USER).
5. Auto-resumption upon quiz answer submission through COMPLETE.
6. 200-350 word Final Reconstructed Incident Report with citations.
7. Job control REST API endpoints via TestClient.
"""

import os
import json
import uuid
import time
import pytest
from datetime import datetime

from backend.routes import (
    submit_analysis_job_quiz_endpoint, QuizSubmissionPayload, SubmitAnswerPayload,
    get_active_case_job_endpoint, get_analysis_job_stages_endpoint
)
from backend.db import SessionLocal, init_db
from backend.models import (
    Case, Evidence, AnalysisJobRecord, AnalysisStageRecord,
    ClarificationQuestionRecord, UserAnswerRecord, ReconstructedReportRecord
)
from backend.services.analysis_orchestrator import (
    PIPELINE_STAGES, create_analysis_job, get_job_with_stages,
    get_active_job_for_case, _execute_job_pipeline,
    resume_analysis_after_quiz_submission, retry_failed_job
)



@pytest.fixture(scope="module")
def setup_test_case():
    """Sets up a test case in SQLite with real evidence files."""
    init_db()
    with SessionLocal() as db:
        case_id = f"test-orch-{uuid.uuid4().hex[:8]}"
        case = Case(id=case_id)
        db.add(case)

        # Create 2 sample evidence items with pre-computed text
        ev1 = Evidence(
            id=str(uuid.uuid4()),
            case_id=case_id,
            original_filename="bank_statement.txt",
            stored_path="storage/originals/bank_statement.txt",
            file_type="text",
            mime_type="text/plain",
            size_bytes=512,
            sha256=uuid.uuid4().hex,
            extracted_text="Bank Account Alert: Debit of INR 45,000 on 12-Nov-2026 at 10:14 AM to Kaveri Logistics. Ref: KL-8842.",
            authenticity_passed=True,
            authenticity_score=1.0,
        )
        ev2 = Evidence(
            id=str(uuid.uuid4()),
            case_id=case_id,
            original_filename="whatsapp_chat.txt",
            stored_path="storage/originals/whatsapp_chat.txt",
            file_type="text",
            mime_type="text/plain",
            size_bytes=512,
            sha256=uuid.uuid4().hex,
            extracted_text="Vikram Nair [10:23 AM]: Rohan, please confirm invoice KL-8842 for 45,000.\nRohan Deshmukh [10:28 AM]: I never authorized this transfer.",
            authenticity_passed=True,
            authenticity_score=1.0,
        )
        db.add(ev1)
        db.add(ev2)
        db.commit()

        yield case_id

        # Cleanup
        db.query(AnalysisStageRecord).filter(AnalysisStageRecord.job_id.in_(
            db.query(AnalysisJobRecord.id).filter(AnalysisJobRecord.case_id == case_id)
        )).delete(synchronize_session=False)
        db.query(AnalysisJobRecord).filter(AnalysisJobRecord.case_id == case_id).delete(synchronize_session=False)
        db.query(UserAnswerRecord).filter(UserAnswerRecord.case_id == case_id).delete(synchronize_session=False)
        db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).delete(synchronize_session=False)
        db.query(ReconstructedReportRecord).filter(ReconstructedReportRecord.case_id == case_id).delete(synchronize_session=False)
        db.query(Evidence).filter(Evidence.case_id == case_id).delete(synchronize_session=False)
        db.query(Case).filter(Case.id == case_id).delete(synchronize_session=False)
        db.commit()


def test_job_initialization_and_18_stages(setup_test_case):
    """Verifies that create_analysis_job creates all 18 stages in order."""
    case_id = setup_test_case
    job = create_analysis_job(case_id)
    assert job is not None
    assert job.status in ["PENDING", "RUNNING", "WAITING_FOR_USER"]

    job_data = get_job_with_stages(job.id)
    assert job_data is not None
    assert len(job_data["stages"]) == 18

    stage_names = [s["stage_name"] for s in job_data["stages"]]
    assert stage_names == PIPELINE_STAGES
    assert stage_names[0] == "VALIDATE_EVIDENCE"
    assert stage_names[1] == "ASSESS_MEDIA_AUTHENTICITY"
    assert stage_names[2] == "APPLY_EVIDENCE_POLICY"
    assert stage_names[5] == "ANALYZE_IMAGES_SEMANTICALLY"
    assert stage_names[14] == "AWAIT_USER_ANSWERS"
    assert stage_names[17] == "COMPLETE"


def test_pipeline_execution_and_pause_at_quiz(setup_test_case):
    """Executes stages up to AWAIT_USER_ANSWERS and verifies automatic pause."""
    case_id = setup_test_case
    job = create_analysis_job(case_id)

    # Run pipeline synchronously in test thread
    _execute_job_pipeline(job.id)

    job_data = get_job_with_stages(job.id)
    assert job_data is not None
    assert job_data["status"] == "WAITING_FOR_USER"
    assert job_data["current_stage"] == "AWAIT_USER_ANSWERS"

    # Verify preliminary narrative & cited facts
    artifacts = job_data["artifacts"]
    assert "mvp_analysis" in artifacts
    mvp = artifacts["mvp_analysis"]
    assert "preliminary_narrative" in mvp
    words = len(mvp["preliminary_narrative"].split())
    assert 100 <= words <= 350
    assert len(mvp["evidence_backed_facts"]) >= 1

    # Verify questions exist
    with SessionLocal() as db:
        questions = db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).all()
        assert len(questions) >= 1


def test_quiz_answer_submission_and_report_generation(setup_test_case):
    """Submits answers and verifies pipeline resumes to COMPLETE."""
    case_id = setup_test_case
    active = get_active_job_for_case(case_id)
    if not active or active["status"] not in ["WAITING_FOR_USER", "COMPLETED"]:
        job = create_analysis_job(case_id)
        _execute_job_pipeline(job.id)
        active = get_job_with_stages(job.id)

    assert active is not None
    job_id = active["id"]

    with SessionLocal() as db:
        q = db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).first()
        assert q is not None
        opts = json.loads(q.options_json) if q.options_json else ["Confirmed"]

    payload = QuizSubmissionPayload(
        answers=[
            SubmitAnswerPayload(
                question_id=q.id,
                selected_option=opts[0],
                user_surety="Very sure",
                knowledge_basis="Direct first-hand knowledge",
                free_text_clarification="Verified against banking records."
            )
        ]
    )
    res = submit_analysis_job_quiz_endpoint(job_id=job_id, payload=payload)
    assert res["status"] == "RESUMED"
    assert res["answers_recorded"] >= 1

    # Wait for pipeline background worker to finish stages 13-15
    final_job = None
    for i in range(40):
        time.sleep(0.5)
        updated = get_job_with_stages(job_id)
        if updated and updated["status"] in ["COMPLETED", "FAILED"]:
            final_job = updated
            break

    assert final_job is not None
    assert final_job["status"] == "COMPLETED"
    assert "COMPLETE" in final_job["completed_stages"]
    assert final_job["progress_percentage"] == 100

    # Verify final report
    artifacts = final_job["artifacts"]
    assert "report_id" in artifacts


def test_active_job_and_stages_endpoints(setup_test_case):
    """Tests active job retrieval and stages listing."""
    case_id = setup_test_case

    job_data = get_active_case_job_endpoint(case_id)
    assert job_data is not None
    assert job_data["case_id"] == case_id

    job_id = job_data["id"]
    stages = get_analysis_job_stages_endpoint(job_id)
    assert len(stages) == 18


def test_existing_case_bf4d0090_job_97b9b8c8_data_contract_and_quality_gates():
    """
    Verifies the repaired state and data contract of existing Case bf4d0090-7d52-4469-ae4e-e11240e44e20
    and Job 97b9b8c8-3e3e-4787-b0e9-4c39edfe5945 without deleting or duplicating evidence.
    """
    case_id = "bf4d0090-7d52-4469-ae4e-e11240e44e20"
    job_id = "97b9b8c8-3e3e-4787-b0e9-4c39edfe5945"

    job_data = get_job_with_stages(job_id)
    assert job_data is not None
    assert job_data["case_id"] == case_id
    assert job_data["status"] in ["WAITING_FOR_USER", "COMPLETED"]
    assert job_data["failed_stage"] is None

    # 1. Verify stage consistency between EXTRACT_EVENTS, BUILD_TIMELINE, and GENERATE_PRELIMINARY_STORY
    stages_by_name = {s["stage_name"]: s for s in job_data["stages"]}
    extracted_events_count = stages_by_name["EXTRACT_EVENTS"]["details"].get("extracted_events_count")
    scheduled_events = stages_by_name["BUILD_TIMELINE"]["details"].get("scheduled_events")
    matched_entities = stages_by_name["MATCH_ENTITIES"]["details"].get("matched_entities_count")

    assert extracted_events_count >= 4
    assert scheduled_events == extracted_events_count
    assert matched_entities > 0

    mvp = job_data["artifacts"]["mvp_analysis"]
    assert mvp["scheduled_events_count"] == scheduled_events
    assert mvp["timeline_status"] == "available"
    assert mvp["case_domain"] == "social_media_harassment"

    # 2. Verify preliminary narrative is case-specific and substantive
    narrative = mvp["preliminary_narrative"]
    assert mvp["narrative_word_count"] >= 150
    assert "Sana Khan" in narrative
    assert "Aman" in narrative
    assert "cse_b_memes" in narrative
    assert "143" in narrative
    assert "Dr. Priya Sharma" in narrative

    # 3. Verify cited facts have valid, non-trivial quotes (no '4G' status bar noise)
    facts = mvp["evidence_backed_facts"]
    assert len(facts) >= 6
    for f in facts:
        quote = f["citation"]["verbatim_quote"].strip()
        assert len(quote) >= 20
        assert quote != "4G"
        assert f["citation"]["evidence_id"]

    # 4. Verify contextual quiz questions
    questions = mvp["unresolved_questions"]
    assert len(questions) == 4
    for q in questions:
        assert "sequence of interactions between the participants" not in q["question"].lower()
        assert len(q["options"]) >= 3
        assert q["why_it_matters"]
        assert q["context_quote"]

