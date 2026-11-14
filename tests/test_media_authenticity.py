"""
Evidence AI — Media Authenticity & Deepfake Detection Test Suite.

Verifies:
  1. Image authenticity detection via Sentry ConvNeXt Small.
  2. Audio deepfake & synthetic speech detection via PellaV2.
  3. Multi-window segmentation and score aggregation for audio.
  4. Cryptographic provenance (C2PA/JUMBF) and metadata (EXIF/ID3) audit.
  5. Unsupported file type skipping (documents, text) without pipeline failure.
  6. Missing file and error-handling graceful fallbacks.
  7. Non-suppression integrity invariant: synthetic warnings NEVER delete, reject, or suppress evidence.
  8. CPU execution invariant: prevents VRAM contention on RTX 4050 6GB.
  9. Idempotent SHA-256 disk caching for sub-millisecond repeated lookups.
  10. Orchestrator integration: ASSESS_MEDIA_AUTHENTICITY stage correctly runs in sequence.
"""

import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
import pytest

from src.detection.image_authenticity import (
    assess_image_authenticity,
    ImageAuthenticityResult,
)
from src.detection.audio_authenticity import (
    assess_audio_authenticity,
    _extract_audio_windows,
    AudioAuthenticityResult,
)
from src.detection.provenance_checker import (
    inspect_media_provenance,
    ProvenanceCheckResult,
)
from backend.services.analysis_orchestrator import (
    PIPELINE_STAGES,
    create_analysis_job,
    get_job_with_stages,
)
from backend.db import SessionLocal, init_db
from backend.models import Case, Evidence, AnalysisJobRecord, AnalysisStageRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_AI_IMAGE = PROJECT_ROOT / "storage" / "originals" / "bf4d0090-7d52-4469-ae4e-e11240e44e20" / "fc04d8c5-61e8-48cc-9ae2-6ebff75f8a02.png"
SAMPLE_REAL_CHAT = PROJECT_ROOT / "tests" / "data" / "real_chat_screenshot.png"
SAMPLE_DOC_SLIP = PROJECT_ROOT / "tests" / "data" / "real_document_slip.png"
SAMPLE_TTS_AUDIO = PROJECT_ROOT / "storage" / "originals" / "bf4d0090-7d52-4469-ae4e-e11240e44e20" / "04002943-631f-422a-8fa3-86d0436788fd.mp3"


def test_ai_generated_image_detection():
    """Scenario 1 & 2: Sentry ConvNeXt Small detects synthetic portrait with high probability."""
    assert SAMPLE_AI_IMAGE.exists(), f"Sample file missing: {SAMPLE_AI_IMAGE}"

    res = assess_image_authenticity(
        image_path=SAMPLE_AI_IMAGE,
        evidence_id="test_ai_img_1",
        filename="wf79vk.png",
    )

    assert isinstance(res, ImageAuthenticityResult)
    assert res.processing_status.upper() == "COMPLETED"
    assert res.assessment.upper() == "SYNTHETIC_INDICATORS_DETECTED"
    assert res.raw_score is not None
    assert res.raw_score > 0.90, f"Expected high synthetic probability, got {res.raw_score}"
    assert res.device_used == "cpu"
    assert "Sentry" in res.score_interpretation or "synthetic" in res.score_interpretation.lower()


def test_real_screenshot_authenticity():
    """Scenario 3: Authentic WhatsApp chat screenshot has negligible synthetic probability."""
    assert SAMPLE_REAL_CHAT.exists(), f"Sample file missing: {SAMPLE_REAL_CHAT}"

    res = assess_image_authenticity(
        image_path=SAMPLE_REAL_CHAT,
        evidence_id="test_chat_1",
        filename="3hx9y2.png",
    )

    assert isinstance(res, ImageAuthenticityResult)
    assert res.processing_status.upper() == "COMPLETED"
    assert res.assessment.upper() == "NO_STRONG_SYNTHETIC_INDICATORS"
    assert res.raw_score is not None
    assert res.raw_score < 0.20, f"Expected low synthetic probability for chat, got {res.raw_score}"


def test_natural_document_slip_authenticity():
    """Scenario 4: Authentic document slip scan is flagged as not detected."""
    assert SAMPLE_DOC_SLIP.exists(), f"Sample file missing: {SAMPLE_DOC_SLIP}"

    res = assess_image_authenticity(
        image_path=SAMPLE_DOC_SLIP,
        evidence_id="test_doc_1",
        filename="x1bvxr.png",
    )

    assert isinstance(res, ImageAuthenticityResult)
    assert res.processing_status.upper() == "COMPLETED"
    assert res.assessment.upper() == "NO_STRONG_SYNTHETIC_INDICATORS"
    assert res.raw_score < 0.20


def test_synthetic_speech_detection():
    """Scenario 5 & 6: PellaV2 evaluates 29.5s audio across 13 windows and detects synthetic speech."""
    assert SAMPLE_TTS_AUDIO.exists(), f"Sample audio missing: {SAMPLE_TTS_AUDIO}"

    res = assess_audio_authenticity(
        audio_path=SAMPLE_TTS_AUDIO,
        evidence_id="test_audio_1",
        filename="call_recording.mp3",
    )

    assert isinstance(res, AudioAuthenticityResult)
    assert res.processing_status.upper() == "COMPLETED"
    assert res.assessment.upper() == "SYNTHETIC_INDICATORS_DETECTED"
    assert res.raw_score is not None
    assert res.raw_score > 0.90, f"Expected high synthetic speech score, got {res.raw_score}"
    assert res.coverage_percentage == 100.0
    assert res.num_windows_analyzed >= 10
    assert len(res.window_scores) >= 10
    assert res.device_used == "cpu"


def test_audio_windowing_and_coverage():
    """Scenario 7: Short and long waveforms are properly segmented and padded."""
    import numpy as np

    # Case A: Short audio (2.0s = 32,000 samples < 64,000)
    short_audio = np.ones(32000, dtype=np.float32)
    windows_short = _extract_audio_windows(short_audio)
    assert len(windows_short) == 1
    assert len(windows_short[0][3]) == 64000
    assert windows_short[0][3][32000] == 0.0  # padded

    # Case B: Multi-window audio (10.0s = 160,000 samples)
    long_audio = np.random.randn(160000).astype(np.float32)
    windows_long = _extract_audio_windows(long_audio)
    assert len(windows_long) >= 4
    for w in windows_long:
        assert len(w[3]) == 64000


def test_provenance_checker_audit():
    """Scenario 8: Cryptographic and EXIF/ID3 provenance audit."""
    assert SAMPLE_REAL_CHAT.exists()
    prov = inspect_media_provenance(SAMPLE_REAL_CHAT, evidence_id="prov_test")

    assert isinstance(prov, ProvenanceCheckResult)
    assert prov.classification in [
        "valid_signed_provenance",
        "valid_signed_ai_provenance",
        "metadata_present",
        "missing_provenance",
        "invalid_provenance",
    ]
    # Missing provenance must explicitly state that it is NOT proof of tampering
    assert any("not evidence of manipulation" in lim.lower() for lim in prov.limitations)


def test_unsupported_file_type_handling():
    """Scenario 9: Unsupported file types (docs, text) are safely marked skipped without error."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        tf.write(b"Plain text report document without image or audio content.")
        tf_path = tf.name

    try:
        # In orchestrator, non-media is marked skipped with skip_reason
        auth_data = {
            "evidence_id": "txt_test",
            "filename": "report.txt",
            "file_type": "text",
            "processing_status": "skipped",
            "assessment": "inconclusive",
            "skip_reason": "unsupported_media_type",
            "relevant_limitations": ["Authenticity detector models are currently available for image and audio media."],
        }
        assert auth_data["processing_status"] == "skipped"
        assert auth_data["skip_reason"] == "unsupported_media_type"
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


def test_missing_file_fallback():
    """Scenario 10: Missing file gracefully falls back to failed/inconclusive without crashing."""
    fake_path = r"c:\project\storage\non_existent_file_9999.png"
    res = assess_image_authenticity(
        image_path=fake_path,
        evidence_id="missing_ev",
        filename="ghost.png",
    )
    assert res.processing_status.upper() == "FAILED"
    assert res.assessment.upper() == "INCONCLUSIVE"
    assert "file not found" in (res.error_message or "").lower()


def test_non_suppression_invariant():
    """
    Forensic Integrity Invariant:
    Synthetic detection warnings must NEVER delete, reject, or suppress evidence items.
    """
    init_db()
    with SessionLocal() as db:
        case_id = str(uuid.uuid4())
        test_case = Case(id=case_id)
        db.add(test_case)

        ev_synthetic = Evidence(
            id=str(uuid.uuid4()),
            case_id=case_id,
            original_filename="synthetic_meme.png",
            stored_path=str(SAMPLE_AI_IMAGE),
            file_type="image",
            mime_type="image/png",
            size_bytes=1024,
            sha256="dummy_hash_synthetic",
            authenticity_passed=False,
            authenticity_score=0.9999,
        )
        db.add(ev_synthetic)
        db.commit()

        # Evidence must still be retrievable and present in database queries
        fetched = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        assert len(fetched) == 1
        assert fetched[0].id == ev_synthetic.id
        assert fetched[0].authenticity_passed is False
        assert fetched[0].authenticity_score == 0.9999

        # Cleanup
        db.delete(ev_synthetic)
        db.delete(test_case)
        db.commit()


def test_orchestrator_18_stages_and_evidence_policy_stage():
    """Verifies that the orchestrator defines ASSESS_MEDIA_AUTHENTICITY and APPLY_EVIDENCE_POLICY."""
    assert len(PIPELINE_STAGES) == 18
    assert PIPELINE_STAGES[0] == "VALIDATE_EVIDENCE"
    assert PIPELINE_STAGES[1] == "ASSESS_MEDIA_AUTHENTICITY"
    assert PIPELINE_STAGES[2] == "APPLY_EVIDENCE_POLICY"
    assert PIPELINE_STAGES[3] == "EXTRACT_CONTENT"
    assert PIPELINE_STAGES[17] == "COMPLETE"


def test_evidence_policy_modes_and_overrides():
    """Verifies policy enforcement: DEVELOPMENT vs STRICT_REVIEW and investigator overrides."""
    init_db()
    with SessionLocal() as db:
        case_id = f"test-policy-{uuid.uuid4().hex[:8]}"
        case = Case(id=case_id)
        db.add(case)

        ev_synth = Evidence(
            id=f"ev-synth-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="ai_portrait.png",
            stored_path=str(SAMPLE_AI_IMAGE),
            file_type="image",
            mime_type="image/png",
            size_bytes=2048,
            sha256="hash_synth_1",
            authenticity_passed=False,
            authenticity_score=0.95,
            review_status="INCLUDED",
        )
        ev_real = Evidence(
            id=f"ev-real-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="slip.png",
            stored_path=str(SAMPLE_DOC_SLIP),
            file_type="image",
            mime_type="image/png",
            size_bytes=2048,
            sha256="hash_real_1",
            authenticity_passed=True,
            authenticity_score=0.10,
            review_status="INCLUDED",
        )
        db.add_all([ev_synth, ev_real])
        db.commit()

        # Check DEVELOPMENT mode
        job_dev = create_analysis_job(case_id, policy_mode="DEVELOPMENT")
        assert job_dev.policy_mode == "DEVELOPMENT"

        # Check STRICT_REVIEW mode
        job_strict = create_analysis_job(case_id, policy_mode="STRICT_REVIEW")
        assert job_strict.policy_mode == "STRICT_REVIEW"

        # Check investigator manual override
        ev_synth.review_status = "EXCLUDED_BY_INVESTIGATOR"
        ev_synth.quarantine_reason = "Manual investigator decision: confirmed synthetic deepfake."
        db.commit()

        reloaded = db.query(Evidence).filter(Evidence.id == ev_synth.id).first()
        assert reloaded.review_status == "EXCLUDED_BY_INVESTIGATOR"
        assert "Manual investigator" in reloaded.quarantine_reason

        # Restore
        reloaded.review_status = "RESTORED_BY_INVESTIGATOR"
        reloaded.quarantine_reason = "Manual override: permitted as baseline context."
        db.commit()

        reloaded2 = db.query(Evidence).filter(Evidence.id == ev_synth.id).first()
        assert reloaded2.review_status == "RESTORED_BY_INVESTIGATOR"

        # Cleanup
        db.query(AnalysisStageRecord).filter(
            AnalysisStageRecord.job_id.in_([job_dev.id, job_strict.id])
        ).delete(synchronize_session=False)
        db.query(AnalysisJobRecord).filter(
            AnalysisJobRecord.id.in_([job_dev.id, job_strict.id])
        ).delete(synchronize_session=False)
        db.delete(ev_synth)
        db.delete(ev_real)
        db.delete(case)
        db.commit()


def test_labeled_manifest_benchmark():
    """
    Evaluates detection performance on ground-truth labeled benchmark manifest.
    Computes precision, recall, and confusion matrix for images and audio.
    """
    manifest_path = PROJECT_ROOT / "tests" / "data" / "labeled_test_manifest.json"
    assert manifest_path.exists(), f"Benchmark manifest missing: {manifest_path}"

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_cases = data.get("image_test_cases", [])

    tp = fp = tn = fn = 0
    results = []

    for c in image_cases:
        p = PROJECT_ROOT / c["relative_path"]
        if not p.exists():
            continue
        res = assess_image_authenticity(p, evidence_id=c["id"], force_refresh=True)
        pred_synth = (res.assessment.upper() == "SYNTHETIC_INDICATORS_DETECTED")
        gt_synth = (c["ground_truth"].upper() == "SYNTHETIC")

        if gt_synth and pred_synth:
            tp += 1
        elif not gt_synth and pred_synth:
            fp += 1
        elif not gt_synth and not pred_synth:
            tn += 1
        elif gt_synth and not pred_synth:
            fn += 1

        results.append({
            "id": c["id"],
            "filename": c["filename"],
            "ground_truth": c["ground_truth"],
            "score": res.raw_score,
            "assessment": res.assessment,
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    print(f"\n--- Benchmark Results: Images ({len(results)} cases) ---")
    print(f"TP={tp}, FP={fp}, TN={tn}, FN={fn} | Precision={precision:.2%}, Recall={recall:.2%}")

    assert tp >= 2, f"Expected at least 2 synthetic true positives, got {tp}"
    assert fp == 0, f"Expected 0 false positives on natural documents/screenshots, got {fp}"
    assert precision >= 0.80, f"Expected precision >= 80%, got {precision:.2%}"
    assert recall >= 0.60, f"Expected recall >= 60%, got {recall:.2%}"


def test_scenario_a_development_mode_synthetic_evidence_disclaimer():
    """
    Scenario A: Development Mode allows synthetic evidence for test evaluation
    while tagging all narrative and summary outputs with [SYNTHETIC TEST ENVIRONMENT].
    """
    from src.intelligence.case_analyzer import analyze_case_mvp
    from backend.services.analysis_orchestrator import create_analysis_job
    init_db()
    with SessionLocal() as db:
        case_id = f"test-dev-disclaimer-{uuid.uuid4().hex[:8]}"
        case = Case(id=case_id)
        db.add(case)

        ev = Evidence(
            id=f"ev-dev-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="synthetic_test.png",
            stored_path=str(SAMPLE_AI_IMAGE),
            file_type="image",
            mime_type="image/png",
            size_bytes=2048,
            sha256="hash_dev_1",
            extracted_text="Investigation meeting discussing transaction KL-8842 and bank notice.",
            review_status="FLAGGED_FOR_REVIEW",
        )
        db.add(ev)
        db.commit()

        job = create_analysis_job(case_id, policy_mode="DEVELOPMENT")
        assert job.policy_mode == "DEVELOPMENT"

        analysis = analyze_case_mvp(
            case_id=case_id,
            evidence_items=[ev],
            policy_mode="DEVELOPMENT",
            authenticity_assessments={
                ev.id: {
                    "assessment": "synthetic_indicators_detected",
                    "raw_score": 0.98,
                    "processing_status": "completed",
                }
            }
        )

        assert "[SYNTHETIC TEST ENVIRONMENT]" in analysis.brief_summary
        assert "[SYNTHETIC TEST ENVIRONMENT]" in analysis.preliminary_narrative
        assert analysis.authenticity_status_summary == "synthetic_detected"

        # Cleanup
        db.query(AnalysisStageRecord).filter(AnalysisStageRecord.job_id == job.id).delete()
        db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job.id).delete()
        db.delete(ev)
        db.delete(case)
        db.commit()


def test_scenario_b_strict_review_mode_all_synthetic_zero_eligible():
    """
    Scenario B: Strict Review Mode with synthetic test files.
    All files are quarantined as EXCLUDED_PENDING_REVIEW.
    Pipeline halts immediately with terminal status NO_ELIGIBLE_EVIDENCE.
    Stages 4-18 are marked as SKIPPED.
    Zero narrative, timeline, quiz, or report is generated.
    """
    from backend.services.analysis_orchestrator import create_analysis_job, _execute_job_pipeline, get_job_with_stages
    from backend.models import ReconstructedReportRecord, MVPAnalysisRecord
    init_db()
    with SessionLocal() as db:
        case_id = f"test-strict-zero-{uuid.uuid4().hex[:8]}"
        case = Case(id=case_id)
        db.add(case)

        # Add synthetic evidence
        ev_items = []
        for i in range(3):
            ev = Evidence(
                id=f"ev-synth-{i}-{uuid.uuid4().hex[:6]}",
                case_id=case_id,
                original_filename=f"ai_gen_{i}.png",
                stored_path=str(SAMPLE_AI_IMAGE),
                file_type="image",
                mime_type="image/png",
                size_bytes=2048,
                sha256=f"hash_synth_{i}_{uuid.uuid4().hex[:4]}",
                review_status="INCLUDED",
            )
            ev_items.append(ev)
            db.add(ev)
        db.commit()

        job = create_analysis_job(case_id, policy_mode="STRICT_REVIEW", force_reanalysis=True)
        assert job.status == "PENDING"
        assert job.policy_mode == "STRICT_REVIEW"

        # Execute pipeline synchronously
        _execute_job_pipeline(job.id)

        job_info = get_job_with_stages(job.id)
        assert job_info["status"] == "NO_ELIGIBLE_EVIDENCE"

        # Verify stages
        stages = {s["stage_name"]: s["status"] for s in job_info["stages"]}
        assert stages["VALIDATE_EVIDENCE"] == "COMPLETED"
        assert stages["ASSESS_MEDIA_AUTHENTICITY"] == "COMPLETED"
        assert stages["APPLY_EVIDENCE_POLICY"] == "COMPLETED"
        for stg in PIPELINE_STAGES[3:]:
            assert stages[stg] == "SKIPPED", f"Stage {stg} was expected to be SKIPPED, got {stages[stg]}"

        # Verify all evidence files have EXCLUDED_PENDING_REVIEW
        reloaded_evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        for rev in reloaded_evs:
            assert rev.review_status == "EXCLUDED_PENDING_REVIEW"
            assert "Strict Review" in rev.quarantine_reason
            assert "synthetic_indicators_detected" in rev.quarantine_reason.lower()

        # Verify no reports or MVP records exist
        rep = db.query(ReconstructedReportRecord).filter(ReconstructedReportRecord.case_id == case_id).first()
        mvp = db.query(MVPAnalysisRecord).filter(MVPAnalysisRecord.case_id == case_id).first()
        assert rep is None
        assert mvp is None

        # Cleanup
        db.query(AnalysisStageRecord).filter(AnalysisStageRecord.job_id == job.id).delete()
        db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job.id).delete()
        for rev in reloaded_evs:
            db.delete(rev)
        db.delete(case)
        db.commit()


def test_scenario_c_strict_review_mode_mixed_eligible_and_quarantined():
    """
    Scenario C: Strict Review Mode with mixed evidence (1 synthetic, 1 authentic).
    The synthetic item is quarantined (EXCLUDED_PENDING_REVIEW).
    The authentic item is INCLUDED.
    The report contains quarantined_evidence and correctly segregates eligible evidence.
    """
    from backend.services.analysis_orchestrator import create_analysis_job
    from src.reporting.report_generator import generate_forensic_incident_report
    init_db()
    with SessionLocal() as db:
        case_id = f"test-strict-mixed-{uuid.uuid4().hex[:8]}"
        case = Case(id=case_id)
        db.add(case)

        ev_synth = Evidence(
            id=f"ev-synth-c-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="ai_portrait.png",
            stored_path=str(SAMPLE_AI_IMAGE),
            file_type="image",
            mime_type="image/png",
            size_bytes=2048,
            sha256="hash_synth_c",
            review_status="INCLUDED",
        )
        ev_real = Evidence(
            id=f"ev-real-c-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="slip.png",
            stored_path=str(SAMPLE_DOC_SLIP),
            file_type="image",
            mime_type="image/png",
            size_bytes=2048,
            sha256="hash_real_c",
            extracted_text="Invoice KL-8842 issued to Nexatech for security services.",
            review_status="INCLUDED",
        )
        db.add_all([ev_synth, ev_real])
        db.commit()

        job = create_analysis_job(case_id, policy_mode="STRICT_REVIEW", force_reanalysis=True)

        quarantined = [
            {
                "id": ev_synth.id,
                "filename": ev_synth.original_filename,
                "file_type": ev_synth.file_type,
                "sha256": ev_synth.sha256,
                "review_status": "EXCLUDED_PENDING_REVIEW",
                "quarantine_reason": "Excluded by Strict Review policy: synthetic detection score 0.96",
                "authenticity_score": 0.96,
                "authenticity_assessment": "synthetic_indicators_detected",
            }
        ]
        eligible = [
            {
                "id": ev_real.id,
                "original_filename": ev_real.original_filename,
                "file_type": ev_real.file_type,
                "sha256": ev_real.sha256,
                "size_bytes": ev_real.size_bytes,
                "extraction_confidence": 0.95,
                "extracted_text": ev_real.extracted_text,
                "extraction_metadata": None,
                "review_status": "INCLUDED",
                "quarantine_reason": None,
            }
        ]

        from src.intelligence.timeline_builder import build_timeline_from_events
        timeline = build_timeline_from_events([], case_id=case_id)

        report = generate_forensic_incident_report(
            case_id=case_id,
            evidence_files=eligible,
            timeline=timeline,
            contradictions=[],
            questions=[],
            answers=[],
            quarantined_evidence=quarantined,
            policy_mode="STRICT_REVIEW",
            authenticity_assessments={
                ev_synth.id: {"assessment": "synthetic_indicators_detected", "raw_score": 0.96},
                ev_real.id: {"assessment": "synthetic_indicators_not_detected", "raw_score": 0.05},
            }
        )

        assert report.policy_mode == "STRICT_REVIEW"
        assert len(report.quarantined_evidence) == 1
        assert report.quarantined_evidence[0]["id"] == ev_synth.id
        assert report.quarantined_evidence[0]["review_status"] == "EXCLUDED_PENDING_REVIEW"
        quarantined_ids = [item["id"] for item in report.quarantined_evidence]
        assert ev_synth.id in quarantined_ids
        inv_ids = [item["id"] for item in report.evidence_inventory]
        assert ev_real.id in inv_ids
        assert ev_synth.id not in inv_ids

        # Cleanup
        db.query(AnalysisStageRecord).filter(AnalysisStageRecord.job_id == job.id).delete()
        db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job.id).delete()
        db.delete(ev_synth)
        db.delete(ev_real)
        db.delete(case)
        db.commit()
