"""
Regression and integration tests for Semantic Vision (Qwen3-VL), Evidence Fusion,
and Dual-Format Reporting (Output A: Brief Summary + Output B: Detailed Report).
"""

import json
from types import SimpleNamespace
import pytest

from src.extraction.semantic_vision import (
    SemanticVisionObservation,
    analyze_image_semantics,
    is_semantic_vision_enabled,
)
from src.intelligence.evidence_fusion import (
    _deduplicate_visual_against_ocr,
    build_unified_evidence_context,
    format_fused_context_for_qwen,
)
from src.intelligence.case_analyzer import analyze_case_mvp
from src.reporting.report_generator import (
    generate_forensic_incident_report,
    render_incident_report_html,
)


def test_semantic_vision_schema_validation_and_aliases():
    obs = SemanticVisionObservation(
        evidence_id="ev-1",
        filename="meme_story.png",
        sha256="abc123",
        content_type="instagram_story",
        visual_description="A social media story screenshot containing a reaction meme targeting Sana.",
        visual_elements=["Top black caption bar", "View count icon 'Seen by 143'"],
        meme_indicators=["Top caption 'When Sana opens her mouth'", "Mocking reaction image"],
        social_media_context=["Handle 'cse_b_memes' at top left", "Story timer '2h'"],
        text_visual_relationships=["Caption frames the reaction photo as mockery of Sana"],
        context_missed_by_plain_ocr=["Story owner toolbar (Activity, Highlight, More) indicating uploader view"],
        uncertainties=["Real legal identity of the person operating 'cse_b_memes'"],
        status="completed",
        inference_time_ms=13220.5,
    )
    assert obs.content_type == "social_post"
    d = obs.to_dict()
    assert d["visual_category"] == "social_post"
    assert "reaction meme" in d["scene_summary"]
    assert "Story owner toolbar" in d["case_relevance"]
    assert d["confidence"] == 0.92
    assert d["processing_time_ms"] == 13220.5


def test_semantic_vision_disabled_flag_returns_skipped(monkeypatch):
    monkeypatch.setenv("EVIDENCE_AI_ENABLE_VISION", "0")
    assert is_semantic_vision_enabled() is False

    obs = analyze_image_semantics(
        image_path="nonexistent_file.png",
        evidence_id="ev-skip",
        filename="nonexistent_file.png",
        vision_enabled=False,
    )
    assert obs.status == "skipped"
    assert obs.content_type == "uncertain"


def test_semantic_vision_safe_fallback_on_missing_file():
    obs = analyze_image_semantics(
        image_path="definitely_missing_evidence_image_999.png",
        evidence_id="ev-fail",
        filename="definitely_missing_evidence_image_999.png",
        vision_enabled=True,
        force_refresh=True,
    )
    assert obs.status == "failed"
    assert "not found" in (obs.error_message or "").lower()


def test_evidence_fusion_deduplication_and_formatting():
    ocr_text = "cse_b_memes 2h When Sana opens her mouth Seen by 143"
    obs_obj = SemanticVisionObservation(
        evidence_id="ev-meme",
        filename="story.png",
        sha256="hash123",
        content_type="meme",
        visual_description="Instagram story meme posted by cse_b_memes mocking Sana.",
        visual_elements=[
            "Text: When Sana opens her mouth",  # Duplicate of OCR
            "Reaction face and Seen by 143 counter",
        ],
        meme_indicators=["Top caption bar 'When Sana opens her mouth'"],
        social_media_context=["Story owner controls at bottom"],
        context_missed_by_plain_ocr=["Captured from the story uploader's own account view"],
        uncertainties=["Actual operator of cse_b_memes"],
        status="completed",
    )
    deduped = _deduplicate_visual_against_ocr(ocr_text, obs_obj)
    assert any("Captured from the story uploader's own account view" in h for h in deduped)
    assert not any(h == "Visible Element: Text: When Sana opens her mouth" for h in deduped)

    ev_mock = SimpleNamespace(
        id="ev-meme",
        original_filename="story.png",
        file_type="image",
        sha256="hash123",
        extracted_text=ocr_text,
        extraction_confidence=0.95,
        segments=json.dumps([]),
        extraction_metadata=json.dumps({}),
    )
    vision_map = {"ev-meme": obs_obj.model_dump()}

    ctx = build_unified_evidence_context(
        case_id="case-1",
        evidence_items=[ev_mock],
        vision_observations=vision_map,
        vision_enabled=True,
    )
    assert ctx.images_completed == 1
    assert ctx.vision_status_summary == "complete"

    prompt_text = format_fused_context_for_qwen(ctx)
    assert "EXTRACTED TEXT" in prompt_text or "PaddleOCR" in prompt_text
    assert "Captured from the story uploader's own account view" in prompt_text


def test_dual_report_brief_summary_and_detailed_report_consistency():
    ev_items = [
        SimpleNamespace(
            id="ev-audio",
            original_filename="confrontation.mp3",
            file_type="audio",
            sha256="h1",
            size_bytes=1024,
            extraction_confidence=0.94,
            extracted_text="Sana: Why did you post that photo of me on the group without asking? Aman: Relax, it was just a joke meme.",
            segments="[]",
            extraction_metadata="{}",
        ),
        SimpleNamespace(
            id="ev-meme",
            original_filename="meme_story.png",
            file_type="image",
            sha256="h2",
            size_bytes=2048,
            extraction_confidence=0.91,
            extracted_text="cse_b_memes 2h When Sana opens her mouth Seen by 143",
            segments="[]",
            extraction_metadata="{}",
        ),
        SimpleNamespace(
            id="ev-slip",
            original_filename="wellness_slip.png",
            file_type="image",
            sha256="h3",
            size_bytes=2048,
            extraction_confidence=0.96,
            extracted_text="UNIVERSITY WELLNESS CENTRE Counselling Visit Slip Student Name: Sana Khan Date: 15 Oct 2024 Reason: Acute stress / online harassment complaint",
            segments="[]",
            extraction_metadata="{}",
        ),
    ]

    vision_obs = {
        "ev-meme": {
            "evidence_id": "ev-meme",
            "filename": "meme_story.png",
            "content_type": "meme",
            "visual_description": "A social media story meme posted on 'cse_b_memes' mocking Sana with caption 'When Sana opens her mouth', viewed by 143 accounts.",
            "visual_elements": ["Reaction meme layout", "Seen by 143 viewer count"],
            "meme_indicators": ["Top black-on-white meme caption bar"],
            "social_media_context": ["Uploader toolbar (Activity, Highlight, More) at bottom"],
            "text_visual_relationships": ["Caption pairs with mocking reaction expression"],
            "context_missed_by_plain_ocr": ["Owner toolbar indicates screenshot was taken from the posting account's view"],
            "uncertainties": ["Legal identity of account holder"],
            "status": "completed",
            "confidence": 0.92,
        }
    }

    analysis_text_only = analyze_case_mvp(
        case_id="case-test",
        evidence_items=ev_items,
        timeline_scheduled_count=2,
        timeline_unscheduled_count=0,
        vision_observations={},
        vision_enabled=False,
    )
    analysis_vision = analyze_case_mvp(
        case_id="case-test",
        evidence_items=ev_items,
        timeline_scheduled_count=2,
        timeline_unscheduled_count=0,
        vision_observations=vision_obs,
        vision_enabled=True,
    )

    assert analysis_text_only.brief_summary_word_count >= 60
    assert analysis_vision.brief_summary_word_count >= 80
    assert len(analysis_text_only.visual_findings) == 0
    assert len(analysis_vision.visual_findings) == 1
    assert "meme" in analysis_vision.brief_summary.lower()

    ev_dicts = [
        {
            "id": e.id,
            "original_filename": e.original_filename,
            "file_type": e.file_type,
            "sha256": e.sha256,
            "size_bytes": e.size_bytes,
            "extraction_confidence": e.extraction_confidence,
            "extracted_text": e.extracted_text,
            "extraction_metadata": e.extraction_metadata,
        }
        for e in ev_items
    ]
    timeline_mock = SimpleNamespace(scheduled_events=[], unscheduled_events=[])
    report = generate_forensic_incident_report(
        case_id="case-test",
        evidence_files=ev_dicts,
        timeline=timeline_mock,
        contradictions=[],
        questions=[],
        answers=[],
        entities_by_type={"PERSON": ["Sana Khan", "Aman"]},
        vision_observations=vision_obs,
        vision_enabled=True,
        mvp_analysis=analysis_vision,
    )
    assert report.brief_summary == analysis_vision.brief_summary
    assert len(report.visual_findings) == 1
    assert len(report.relevant_participants) >= 2
    assert len(report.attributed_claims_and_allegations) >= 1
    html = render_incident_report_html(report)
    assert "Brief Incident Summary" in html
    assert "Relevant Visual Semantic Observations" in html
