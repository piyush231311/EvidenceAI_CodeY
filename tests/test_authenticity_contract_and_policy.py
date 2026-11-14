"""
Regression Test Suite for Evidence AI Media Authenticity Scoring Contract,
Eligibility Policy Invariants, and Inventory Counter Consistency.
"""

import uuid
import pytest
from pathlib import Path

from src.detection.image_authenticity import assess_image_authenticity, ImageAuthenticityResult
from src.detection.audio_authenticity import assess_audio_authenticity, AudioAuthenticityResult
from backend.services.analysis_orchestrator import create_analysis_job, _execute_job_pipeline, get_job_with_stages
from backend.db import SessionLocal, init_db
from backend.models import Case, Evidence, AnalysisJobRecord, AnalysisStageRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_AI_IMAGE = PROJECT_ROOT / "storage" / "originals" / "bf4d0090-7d52-4469-ae4e-e11240e44e20" / "fc04d8c5-61e8-48cc-9ae2-6ebff75f8a02.png"
SAMPLE_REAL_CHAT = PROJECT_ROOT / "tests" / "data" / "real_chat_screenshot.png"
SAMPLE_TTS_AUDIO = PROJECT_ROOT / "storage" / "originals" / "bf4d0090-7d52-4469-ae4e-e11240e44e20" / "04002943-631f-422a-8fa3-86d0436788fd.mp3"


def test_scoring_contract_image():
    """Invariant 1 & 2: Scoring contract fields are populated and uncalibrated scores are not claimed as probabilities."""
    assert SAMPLE_AI_IMAGE.exists()
    res = assess_image_authenticity(SAMPLE_AI_IMAGE, evidence_id="ev_img_contract_test")
    assert isinstance(res, ImageAuthenticityResult)

    data = res.model_dump()
    assert "evidence_id" in data
    assert "detector_model" in data and data["detector_model"] == "sentry-convnext-small"
    assert "model_version" in data and data["model_version"] == "5.1.0"
    assert "policy_version" in data and data["policy_version"] == "2.0.0"
    assert data["inference_executed"] is True
    assert "raw_model_output" in data and isinstance(data["raw_model_output"], dict)
    assert "synthetic_score" in data and data["synthetic_score"] is not None
    assert data["synthetic_score"] == res.raw_score
    assert "score_type" in data and data["score_type"] in ["raw_uncalibrated_softmax", "c2pa_cryptographic_assertion"]
    assert data["calibrated_probability"] is None  # Uncalibrated by design
    assert data["assessment_status"] in ["SYNTHETIC_INDICATORS_DETECTED", "NO_STRONG_SYNTHETIC_INDICATORS", "INCONCLUSIVE"]
    assert "assessment_reason" in data and len(data["assessment_reason"]) > 0
    assert data["decision_threshold"] == 0.50
    assert data["processing_status"] == "COMPLETED"
    assert isinstance(data["relevant_limitations"], list) and len(data["relevant_limitations"]) >= 2


def test_scoring_contract_audio():
    """Invariant 1 & 2: Audio scoring contract populated and uncalibrated scores strictly typed."""
    assert SAMPLE_TTS_AUDIO.exists()
    res = assess_audio_authenticity(SAMPLE_TTS_AUDIO, evidence_id="ev_aud_contract_test")
    assert isinstance(res, AudioAuthenticityResult)

    data = res.model_dump()
    assert data["detector_model"] == "pellav2-audio-deepfake-detector"
    assert data["model_version"] == "2.0.0"
    assert data["policy_version"] == "2.0.0"
    assert data["inference_executed"] is True
    assert isinstance(data["raw_model_output"], dict)
    assert data["synthetic_score"] is not None
    assert data["score_type"] == "w2v_bert_window_aggregate"
    assert data["calibrated_probability"] is None
    assert data["assessment_status"] == "SYNTHETIC_INDICATORS_DETECTED"
    assert data["decision_threshold"] == 0.50
    assert data["processing_status"] == "COMPLETED"


def test_inconclusive_and_failed_files_never_quarantined():
    """
    Invariant 5 & 6:
    Inconclusive, unsupported, or failed assessments must NEVER trigger quarantine.
    They remain INCLUDED in active reconstruction.
    """
    init_db()
    with SessionLocal() as db:
        case_id = f"test-inconclusive-safety-{uuid.uuid4().hex[:8]}"
        case = Case(id=case_id)
        db.add(case)

        # 1. Unsupported text file
        ev_unsupported = Evidence(
            id=f"ev-unsup-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="notes.txt",
            stored_path="storage/notes.txt",
            file_type="text",
            mime_type="text/plain",
            size_bytes=100,
            sha256="hash_unsup",
            review_status="INCLUDED",
        )
        # 2. Failed audio (missing path)
        ev_failed = Evidence(
            id=f"ev-fail-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="missing.mp3",
            stored_path="storage/missing_file_404.mp3",
            file_type="audio",
            mime_type="audio/mp3",
            size_bytes=100,
            sha256="hash_fail",
            review_status="INCLUDED",
        )
        # 3. Authentic screenshot
        ev_real = Evidence(
            id=f"ev-real-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="real_chat.png",
            stored_path=str(SAMPLE_REAL_CHAT),
            file_type="image",
            mime_type="image/png",
            size_bytes=200,
            sha256="hash_real_chat",
            review_status="INCLUDED",
        )
        db.add_all([ev_unsupported, ev_failed, ev_real])
        db.commit()

        # Run under STRICT_REVIEW
        job = create_analysis_job(case_id, policy_mode="STRICT_REVIEW", force_reanalysis=True)
        _execute_job_pipeline(job.id)

        # Check evidence review_statuses
        reloaded = {e.id: e for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()}

        # Inconclusive / unsupported / failed / real files MUST ALL BE INCLUDED, NEVER quarantined!
        assert reloaded[ev_unsupported.id].review_status == "INCLUDED"
        assert reloaded[ev_unsupported.id].quarantine_reason is None

        assert reloaded[ev_failed.id].review_status == "INCLUDED"
        assert reloaded[ev_failed.id].quarantine_reason is None

        assert reloaded[ev_real.id].review_status == "INCLUDED"
        assert reloaded[ev_real.id].quarantine_reason is None

        # Cleanup
        db.query(AnalysisStageRecord).filter(AnalysisStageRecord.job_id == job.id).delete()
        db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job.id).delete()
        db.delete(ev_unsupported)
        db.delete(ev_failed)
        db.delete(ev_real)
        db.delete(case)
        db.commit()


def test_default_review_workflow_flags_evidence():
    """
    Invariant 4 & 7:
    Default review workflow flags synthetic evidence as FLAGGED_FOR_REVIEW
    for investigator examination rather than automatically removing it.
    """
    init_db()
    with SessionLocal() as db:
        case_id = f"test-default-review-{uuid.uuid4().hex[:8]}"
        case = Case(id=case_id)
        db.add(case)

        ev_synth = Evidence(
            id=f"ev-synth-dev-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            original_filename="synth_portrait.png",
            stored_path=str(SAMPLE_AI_IMAGE),
            file_type="image",
            mime_type="image/png",
            size_bytes=1000,
            sha256="hash_synth_dev",
            review_status="INCLUDED",
        )
        db.add(ev_synth)
        db.commit()

        job = create_analysis_job(case_id, policy_mode="DEVELOPMENT", force_reanalysis=True)
        _execute_job_pipeline(job.id)

        reloaded = db.query(Evidence).filter(Evidence.id == ev_synth.id).first()
        assert reloaded.review_status == "FLAGGED_FOR_REVIEW"
        assert "Flagged for Review" in reloaded.quarantine_reason

        # Cleanup
        db.query(AnalysisStageRecord).filter(AnalysisStageRecord.job_id == job.id).delete()
        db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job.id).delete()
        db.delete(ev_synth)
        db.delete(case)
        db.commit()
