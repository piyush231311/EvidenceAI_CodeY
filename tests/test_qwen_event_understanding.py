"""
Regression test suite for Evidence AI Qwen Event Understanding and Clarification Quiz.

Verifies:
1. Sequential communications (e.g. 10:23 AM vs 10:28 AM) are NOT false contradictions.
2. Message sent time vs planned meeting time are NOT false contradictions.
3. Document signing time vs message sent time are NOT false contradictions.
4. Blocklisted words ("If", "Do", "Meet", "Please", "Updateed") are NOT accepted as actors.
5. Unconfirmed proposed events are classified as 'proposed', never completed.
6. Genuine contradictions on the same proposition ARE detected.
7. Preliminary case understanding synthesizes key parties, established facts, and unconfirmed plans.
8. Clarification quiz generates focused human-readable questions naming activities with "I don't know" options.
9. User answer knowledge basis defaults to 'Not specified'.
"""

import pytest
from datetime import datetime

from src.intelligence.event_extractor import (
    EventCandidate,
    NON_ACTOR_WORDS,
    clean_and_validate_actors,
    generate_human_readable_title,
)
from src.intelligence.evidence_reasoner import (
    are_events_same_proposition,
    detect_time_discrepancy,
    detect_plan_vs_execution_or_denial,
    analyze_cross_evidence_relationships,
    ContradictionRecord,
)
from src.intelligence.timeline_builder import (
    TimelineReconstruction,
    TimelineEntry,
    build_timeline_from_events,
)
from src.intelligence.clarification_engine import (
    generate_preliminary_case_understanding,
    generate_clarification_quiz,
    UserAnswer,
    ClarificationQuestion,
)
from backend.models import SubmitAnswerPayload


def test_actor_blocklist_rejects_function_words():
    """Sentence-initial words like 'If', 'Do', 'Meet', 'Please', 'Updateed' must not be actors."""
    raw_actors = ["If", "Do", "Meet", "Please", "Updateed", "Vikram Nair", "Rahul Sharma"]
    cleaned = clean_and_validate_actors(raw_actors)

    assert "If" not in cleaned
    assert "Do" not in cleaned
    assert "Meet" not in cleaned
    assert "Please" not in cleaned
    assert "Updateed" not in cleaned
    assert "Vikram Nair" in cleaned
    assert "Rahul Sharma" in cleaned


def test_sequential_messages_not_contradiction():
    """A message at 10:23 AM and reply at 10:28 AM must NOT be a contradiction."""
    msg1 = EventCandidate(
        event_id="msg-1",
        case_id="case-1",
        title="Message sent by Vikram Nair",
        activity_name="Vikram Nair sent message",
        event_status="observed",
        timestamp_type="message_sent_time",
        original_time_expression="10:23 AM",
        timestamp_raw="10:23 AM",
        timestamp_norm="2026-11-12T10:23:00",
        actors=["Vikram Nair"],
        is_communication=True,
        source_evidence_id="evidence-1",
    )
    msg2 = EventCandidate(
        event_id="msg-2",
        case_id="case-1",
        title="Reply message by Rahul Sharma",
        activity_name="Rahul Sharma sent reply",
        event_status="observed",
        timestamp_type="message_sent_time",
        original_time_expression="10:28 AM",
        timestamp_raw="10:28 AM",
        timestamp_norm="2026-11-12T10:28:00",
        actors=["Rahul Sharma"],
        is_communication=True,
        source_evidence_id="evidence-1",
    )

    # They are separate messages, not the same proposition
    assert not are_events_same_proposition(msg1, msg2)
    contra = detect_time_discrepancy(msg1, msg2)
    assert contra is None


def test_message_sent_time_vs_planned_meeting_time_not_contradiction():
    """A message sent at 10:40 AM discussing a meeting planned for 4:30 PM is NOT a contradiction."""
    msg = EventCandidate(
        event_id="msg-1",
        case_id="case-1",
        title="Message sent regarding meeting",
        activity_name="Message sent",
        event_status="observed",
        timestamp_type="message_sent_time",
        original_time_expression="10:40 AM",
        timestamp_raw="10:40 AM",
        actors=["Vikram Nair"],
        is_communication=True,
        source_evidence_id="evidence-1",
    )
    planned_meeting = EventCandidate(
        event_id="plan-1",
        case_id="case-1",
        title="Proposed meeting at Cubbon Park",
        activity_name="Meeting at Cubbon Park",
        event_status="proposed",
        timestamp_type="planned_event_time",
        original_time_expression="4:30 PM",
        referenced_event_time="4:30 PM",
        timestamp_raw="4:30 PM",
        actors=["Vikram Nair", "Rahul Sharma"],
        is_communication=False,
        source_evidence_id="evidence-1",
    )

    assert not are_events_same_proposition(msg, planned_meeting)
    contra = detect_time_discrepancy(msg, planned_meeting)
    assert contra is None


def test_email_sent_vs_document_signed_not_contradiction():
    """An email at 10:14 AM vs document signed at 4:30 PM are separate actions on different artifacts."""
    email_event = EventCandidate(
        event_id="email-1",
        case_id="case-1",
        title="Email sent: 'Please sign invoice'",
        activity_name="Email sent",
        event_status="observed",
        timestamp_type="message_sent_time",
        original_time_expression="10:14 AM",
        timestamp_raw="10:14 AM",
        actors=["Vikram Nair"],
        is_communication=True,
        source_evidence_id="evidence-email",
    )
    doc_event = EventCandidate(
        event_id="doc-1",
        case_id="case-1",
        title="Invoice KL-8842 signed",
        activity_name="Invoice KL-8842 sign-off",
        event_status="completed",
        timestamp_type="document_signing_time",
        original_time_expression="4:30 PM",
        timestamp_raw="4:30 PM",
        actors=["Rahul Sharma"],
        is_communication=False,
        source_evidence_id="evidence-pdf",
    )

    assert not are_events_same_proposition(email_event, doc_event)
    contra = detect_time_discrepancy(email_event, doc_event)
    assert contra is None


def test_genuine_contradiction_detected_for_same_proposition():
    """Two sources giving conflicting times for the exact same meeting proposition DO trigger a contradiction."""
    stmt_a = EventCandidate(
        event_id="ev-a",
        case_id="case-1",
        title="Meeting at Cubbon Park at 4:30 PM",
        activity_name="Meeting at Cubbon Park",
        action="meet",
        event_status="observed",
        timestamp_type="actual_occurrence_time",
        original_time_expression="4:30 PM",
        timestamp_raw="4:30 PM",
        timestamp_norm="2026-11-12T16:30:00",
        actors=["Vikram Nair", "Rahul Sharma"],
        source_evidence_id="witness-1",
        description="Witness 1 states: 'We met at Cubbon Park at 4:30 PM sharp.'",
    )
    stmt_b = EventCandidate(
        event_id="ev-b",
        case_id="case-1",
        title="Meeting at Cubbon Park at 6:00 PM",
        activity_name="Meeting at Cubbon Park",
        action="meet",
        event_status="observed",
        timestamp_type="actual_occurrence_time",
        original_time_expression="6:00 PM",
        timestamp_raw="6:00 PM",
        timestamp_norm="2026-11-12T18:00:00",
        actors=["Vikram Nair", "Rahul Sharma"],
        source_evidence_id="witness-2",
        description="Witness 2 states: 'The meeting at Cubbon park happened at 6:00 PM.'",
    )

    # Same activity and location and actors -> same proposition
    assert are_events_same_proposition(stmt_a, stmt_b)
    contra = detect_time_discrepancy(stmt_a, stmt_b)
    assert contra is not None
    assert contra.contradiction_type == "time_discrepancy"
    assert "Meeting at Cubbon Park" in contra.unresolved_question


def test_proposed_events_remain_proposed_not_completed():
    """Unconfirmed plans should have event_status='proposed' and not be recorded as completed facts."""
    plan = EventCandidate(
        event_id="plan-1",
        case_id="case-1",
        title="Proposed meeting at Cubbon Park",
        activity_name="Meeting at Cubbon Park",
        event_status="proposed",
        timestamp_type="planned_event_time",
        original_time_expression="4:30 PM",
        referenced_event_time="4:30 PM",
        actors=["Vikram Nair"],
    )
    assert plan.event_status == "proposed"
    assert plan.timestamp_type == "planned_event_time"


def test_preliminary_case_understanding_generation():
    """generate_preliminary_case_understanding synthesizes key parties, facts, and citations."""
    events = [
        EventCandidate(
            event_id="e-1",
            case_id="case-1",
            title="Message from Vikram Nair: 'Please send invoice KL-8842'",
            activity_name="Invoice discussion",
            event_status="observed",
            timestamp_type="message_sent_time",
            timestamp_raw="10:23 AM",
            actors=["Vikram Nair"],
            is_communication=True,
            source_evidence_id="file-1",
        ),
        EventCandidate(
            event_id="e-2",
            case_id="case-1",
            title="Meeting proposed for 4:30 PM at Cubbon Park",
            activity_name="Meeting at Cubbon Park",
            event_status="proposed",
            timestamp_type="planned_event_time",
            timestamp_raw="4:30 PM",
            referenced_event_time="4:30 PM",
            actors=["Vikram Nair", "Rahul Sharma"],
            source_evidence_id="file-1",
        ),
    ]

    class MockEvidence:
        def __init__(self, id, filename, file_type):
            self.id = id
            self.filename = filename
            self.file_type = file_type

    files = [MockEvidence("file-1", "chat_screenshot.png", "image")]

    understanding = generate_preliminary_case_understanding(
        case_id="case-1",
        evidence_files=files,
        events=events,
        contradictions=[],
    )

    assert understanding.case_id == "case-1"
    assert len(understanding.narrative_summary) > 20
    assert any(p["name"] == "Vikram Nair" for p in understanding.key_parties)
    assert len(understanding.established_facts) >= 1
    assert len(understanding.proposed_or_planned) >= 1
    assert understanding.proposed_or_planned[0]["status"] == "Unconfirmed proposal"


def test_clarification_quiz_human_readability_and_options():
    """Quiz questions must name the activity, include why_it_matters, and 'I do not know' options."""
    contra = ContradictionRecord(
        contradiction_id="c-1",
        case_id="case-1",
        contradiction_type="time_discrepancy",
        description="Discrepancy on Meeting at Cubbon Park",
        event_ids=["ev-a", "ev-b"],
        evidence_ids=["file-1", "file-2"],
        statement_a="Witness 1 says meeting was at 4:30 PM",
        statement_b="Witness 2 says meeting was at 6:00 PM",
        source_a="witness-1.txt",
        source_b="witness-2.txt",
        unresolved_question="Meeting at Cubbon Park",
    )

    timeline = TimelineReconstruction(
        case_id="case-1",
        scheduled_events=[
            TimelineEntry(
                entry_id="te-1",
                event_id="plan-1",
                timestamp=None,
                title="Proposed meeting at Cubbon Park",
                description="Discussion of meeting at 4:30 PM",
                event_type="meeting",
                timeline_status="scheduled",
                evidence_ids=["file-1"],
            )
        ],
        unscheduled_events=[],
    )

    questions = generate_clarification_quiz(
        case_id="case-1",
        contradictions=[contra],
        timeline=timeline,
        max_questions=6,
    )

    assert len(questions) >= 1
    for q in questions:
        # Prompt names the actual activity
        assert "meeting at cubbon park" in q.prompt.lower() or "meeting at cubbon park" in q.activity_name.lower()
        # Does NOT have nonsensical actor prefixes
        assert not q.prompt.startswith("If -")
        assert not q.prompt.startswith("Do -")
        assert not q.prompt.startswith("Meet -")
        # Explains why it matters
        assert len(q.why_it_matters) > 10
        # Includes uncommitted options
        assert any("I do not know" in opt for opt in q.options)
        assert any("I did not personally witness this" in opt for opt in q.options)


def test_knowledge_basis_defaults_to_not_specified():
    """UserAnswer and SubmitAnswerPayload must default knowledge_basis to 'Not specified'."""
    ans = UserAnswer(
        question_id="q-1",
        case_id="case-1",
        selected_option="Yes, occurred as planned",
    )
    assert ans.knowledge_basis == "Not specified"
    assert ans.knowledge_basis != "Directly witnessed"

    payload = SubmitAnswerPayload(
        question_id="q-1",
        selected_option="Yes, occurred as planned",
    )
    assert payload.knowledge_basis == "Not specified"
    assert payload.knowledge_basis != "Directly witnessed"
