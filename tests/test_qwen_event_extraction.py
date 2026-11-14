"""
Regression and Integration Tests for Evidence AI Event Extraction, Timeline, Clarification, and Reporting.

Covers:
- Modality & tense detection (plans/promises/allegations vs completed occurrences)
- Grounded verbatim text span validation
- Unanchored time expression handling without timestamp fabrication
- Cross-evidence contradiction detection
- Targeted clarification quiz generation with ordinal surety (0-4)
- Non-alteration of underlying documentary evidence
- Forensic incident report generation with SHA-256 integrity hashes & disclaimers
"""

import pytest
from datetime import datetime
from src.intelligence.event_extractor import (
    EventCandidate,
    detect_modality_and_tense,
    validate_grounded_spans,
    deterministic_grounded_event_extraction,
)
from src.intelligence.timeline_builder import (
    parse_event_temporal_anchor,
    build_timeline_from_events,
)
from src.intelligence.evidence_reasoner import (
    analyze_cross_evidence_relationships,
)
from src.intelligence.clarification_engine import (
    generate_clarification_quiz,
    apply_clarifications_to_timeline,
    UserAnswer,
    ClarificationQuestion,
    SURETY_MAPPING,
)
from src.reporting.report_generator import (
    generate_forensic_incident_report,
    render_incident_report_html,
    AI_ASSISTED_ANALYSIS_DISCLAIMER,
)


def test_modality_and_tense_detection():
    """Verify that statements of intent, future delivery, or allegations are not treated as completed events."""
    # Planned/future delivery
    m1, e1, f1 = detect_modality_and_tense("Vikram Nair said he will deliver the package tomorrow at 4:30 PM.")
    assert m1 == "planned"
    assert e1 == "plan_or_promise"

    # Allegation
    m2, e2, f2 = detect_modality_and_tense("Rohan claimed that the signature was forged.")
    assert m2 == "alleged"
    assert e2 == "attributed_statement"

    # Denial
    m3, e3, f3 = detect_modality_and_tense("Vikram denies having ever visited the warehouse.")
    assert m3 == "denied"

    # Completed past event
    m4, e4, f4 = detect_modality_and_tense("Payment of INR 50,000 received at 10:14 AM.")
    assert m4 == "completed"
    assert e4 == "explicit_statement"


def test_grounded_span_validation():
    """Verify that hallucinated or non-verbatim text spans fail validation."""
    source_chunk = (
        "Invoice approved by Vikram Nair on November 12th. Payment sent via NEFT. "
        "Security guard logged vehicle entry at 10:30 AM."
    )

    # Valid candidate with grounded spans
    valid_cand = EventCandidate(
        event_id="cand-valid",
        case_id="case-1",
        event_type="financial_transaction",
        title="Invoice Approval",
        description="Invoice approved",
        action="approved",
        supporting_text_spans=["Invoice approved by Vikram Nair", "Payment sent via NEFT"],
    )
    result_valid = validate_grounded_spans(valid_cand, source_chunk)
    assert result_valid.validation_status == "valid"
    assert len(result_valid.uncertainty_flags) == 0

    # Fabricated / hallucinated span candidate
    invalid_cand = EventCandidate(
        event_id="cand-invalid",
        case_id="case-1",
        event_type="incident",
        title="Confession",
        description="Confession signed",
        action="confessed",
        supporting_text_spans=["Vikram signed the confession in the presence of police"],
    )
    result_invalid = validate_grounded_spans(invalid_cand, source_chunk)
    assert result_invalid.validation_status == "suspicious_citation"
    assert any("span_not_found" in flag for flag in result_invalid.uncertainty_flags)


def test_unanchored_times_remain_unscheduled():
    """Verify that ambiguous time expressions without dates or meridians are not assigned fabricated timestamps."""
    # Ambiguous expression
    ts, prec, unscheduled = parse_event_temporal_anchor("10:14")
    assert unscheduled is True
    assert ts is None

    # Fully anchored expression
    ts2, prec2, unscheduled2 = parse_event_temporal_anchor("2026-11-12 10:30:00")
    assert unscheduled2 is False
    assert ts2 is not None


def test_timeline_chronological_ordering_and_unscheduled_bin():
    """Verify that scheduled events sort chronologically and unanchored events sit in the unscheduled section."""
    ev_anchored_early = EventCandidate(
        event_id="ev-1",
        case_id="case-1",
        event_type="communication",
        title="Morning Email",
        description="First email sent",
        actors=["Alice"],
        action="sent",
        original_time_expression="2026-11-12 09:00:00",
        normalized_start_time=datetime(2026, 11, 12, 9, 0, 0),
        temporal_precision="minute",
        evidence_ids=["ev-doc-1"],
        source_segment_ids=["s-1"],
        supporting_text_spans=["First email sent at 9:00 AM"],
        modality="completed",
        explicit_or_inferred="explicit_statement",
    )

    ev_anchored_late = EventCandidate(
        event_id="ev-2",
        case_id="case-1",
        event_type="physical_action",
        title="Afternoon Meeting",
        description="Delivery made",
        actors=["Bob"],
        action="delivered",
        original_time_expression="2026-11-12 14:00:00",
        normalized_start_time=datetime(2026, 11, 12, 14, 0, 0),
        temporal_precision="minute",
        evidence_ids=["ev-doc-2"],
        source_segment_ids=["s-2"],
        supporting_text_spans=["Delivery completed at 2:00 PM"],
        modality="completed",
        explicit_or_inferred="explicit_statement",
    )

    ev_unanchored = EventCandidate(
        event_id="ev-3",
        case_id="case-1",
        event_type="communication",
        title="Unspecified Chat",
        description="Chat occurred",
        actors=["Alice", "Bob"],
        action="discussed",
        original_time_expression="sometime in the evening",
        normalized_start_time=None,
        temporal_precision="unanchored",
        evidence_ids=["ev-doc-1"],
        source_segment_ids=["s-3"],
        supporting_text_spans=["We discussed this sometime in the evening"],
        modality="completed",
        explicit_or_inferred="explicit_statement",
    )

    # Pass in reversed order to test sorting
    reconstruction = build_timeline_from_events([ev_anchored_late, ev_unanchored, ev_anchored_early], case_id="case-1")
    
    assert len(reconstruction.scheduled_events) == 2
    assert len(reconstruction.unscheduled_events) == 1
    # Check ascending chronological sort
    assert reconstruction.scheduled_events[0].event_id == "ev-1"
    assert reconstruction.scheduled_events[1].event_id == "ev-2"
    assert reconstruction.unscheduled_events[0].event_id == "ev-3"


def test_contradiction_detection():
    """Verify that contradictory times and plan-vs-execution mismatches are flagged."""
    ev_plan = EventCandidate(
        event_id="ev-plan",
        case_id="case-1",
        event_type="delivery",
        title="Scheduled Delivery",
        description="Delivery planned for 4:30 PM",
        actors=["Vikram"],
        action="deliver",
        original_time_expression="4:30 PM",
        normalized_start_time=None,
        temporal_precision="unanchored",
        evidence_ids=["doc-a"],
        source_segment_ids=["s-1"],
        supporting_text_spans=["Vikram will deliver package at 4:30 PM"],
        modality="planned",
        explicit_or_inferred="plan_or_promise",
    )

    ev_actual = EventCandidate(
        event_id="ev-actual",
        case_id="case-1",
        event_type="delivery",
        title="Delivery Received",
        description="Package received at 5:15 PM",
        actors=["Vikram"],
        action="received",
        original_time_expression="5:15 PM",
        normalized_start_time=None,
        temporal_precision="unanchored",
        evidence_ids=["doc-b"],
        source_segment_ids=["s-2"],
        supporting_text_spans=["Package was received late at 5:15 PM"],
        modality="completed",
        explicit_or_inferred="explicit_statement",
    )

    timeline = build_timeline_from_events([ev_plan, ev_actual], case_id="case-1")
    analysis = analyze_cross_evidence_relationships([ev_plan, ev_actual], timeline)
    assert len(analysis.contradictions) >= 1
    # Check that discrepancy is identified
    types = [c.contradiction_type for c in analysis.contradictions]
    assert "time_discrepancy" in types or "plan_vs_execution" in types


def test_clarification_quiz_and_ordinal_surety():
    """Verify that clarification quiz questions generate properly and record ordinal surety without altering evidence."""
    ev_unanchored = EventCandidate(
        event_id="ev-ambig",
        case_id="case-1",
        event_type="incident",
        title="Security Alert",
        description="Alarm triggered",
        actors=["Security"],
        action="triggered",
        original_time_expression="around 10",
        normalized_start_time=None,
        temporal_precision="unanchored",
        evidence_ids=["doc-c"],
        source_segment_ids=["s-1"],
        supporting_text_spans=["Alarm was triggered around 10"],
        modality="completed",
        explicit_or_inferred="explicit_statement",
    )

    recon = build_timeline_from_events([ev_unanchored], case_id="case-1")
    quiz = generate_clarification_quiz(case_id="case-1", contradictions=[], timeline=recon)
    assert len(quiz) >= 1
    q = quiz[0]
    assert "Can you clarify when this occurred?" in q.prompt or "unspecified" in q.prompt

    # Test ordinal surety score mapping
    assert SURETY_MAPPING["Very sure"] == 4
    assert SURETY_MAPPING["Fairly sure"] == 3
    assert SURETY_MAPPING["Somewhat sure"] == 2
    assert SURETY_MAPPING["Unsure"] == 1
    assert SURETY_MAPPING["Do not remember"] == 0

    # User answer
    ans = UserAnswer(
        answer_id="ans-1",
        question_id=q.question_id,
        case_id="case-1",
        event_id=ev_unanchored.event_id,
        selected_option="Occurred on the same date as the surrounding case evidence",
        free_text_clarification="Logged in security guard paper log",
        user_surety="Very sure",
        surety_score=4,
        knowledge_basis="Official record",
    )

    # Reconstruct timeline incorporating answer
    q_map = {q.question_id: q}
    updated_recon = apply_clarifications_to_timeline(recon, [ans], q_map)

    # The timeline should mark clarification applied
    all_entries = updated_recon.scheduled_events + updated_recon.unscheduled_events
    matching_entry = next((e for e in all_entries if e.event_id == ev_unanchored.event_id), None)
    assert matching_entry is not None
    assert matching_entry.timeline_status == "user_reported"
    assert "User Clarification" in matching_entry.description
    # Raw source span must remain intact
    assert "Alarm was triggered around 10" in matching_entry.supporting_text_spans


def test_forensic_incident_report_generation():
    """Verify that the forensic incident report synthesizes evidence, SHA-256 hashes, and includes disclaimers."""
    evidence_items = [
        {
            "id": "e-1",
            "filename": "security_memo.pdf",
            "file_type": "text",
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "authenticity_passed": True,
            "extraction_method": "Doc Parser",
        }
    ]

    ev_event = EventCandidate(
        event_id="ev-1",
        case_id="case-test",
        event_type="communication",
        title="Memo Circulated",
        description="Security memo issued",
        actors=["Director"],
        action="issued",
        original_time_expression="2026-11-12 10:00:00",
        normalized_start_time=datetime(2026, 11, 12, 10, 0, 0),
        temporal_precision="minute",
        evidence_ids=["e-1"],
        source_segment_ids=["s-1"],
        supporting_text_spans=["Security memo issued on 2026-11-12"],
        modality="completed",
        explicit_or_inferred="explicit_statement",
    )

    recon = build_timeline_from_events([ev_event], case_id="case-test")
    report = generate_forensic_incident_report(
        case_id="case-test",
        evidence_files=evidence_items,
        timeline=recon,
        contradictions=[],
        questions=[],
        answers=[],
    )

    assert report.case_id == "case-test"
    assert len(report.evidence_inventory) == 1
    assert report.evidence_inventory[0]["sha256"] == evidence_items[0]["sha256"]
    assert AI_ASSISTED_ANALYSIS_DISCLAIMER in report.technical_disclaimer

    # Test HTML rendering
    html = render_incident_report_html(report)
    assert "<!DOCTYPE html>" in html
    assert "case-test" in html
    assert evidence_items[0]["sha256"] in html
    assert "AI-ASSISTED" in html or "DISCLAIMER" in html
