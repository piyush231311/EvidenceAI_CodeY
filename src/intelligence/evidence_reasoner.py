"""
Cross-Evidence Corroboration & Contradiction Reasoning Engine for Evidence AI.

Analyzes relationships across event candidates and evidence files to discover:
- Corroborating statements across independent sources
- Contradictory dates and times (e.g. 4:30 PM delivery planned vs 5:15 PM actual)
- Plan vs execution discrepancies (promise != delivery)
- Denials vs allegations
- Missing supporting information and provenance overlaps
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from src.intelligence.event_extractor import EventCandidate
from src.intelligence.timeline_builder import TimelineEntry, TimelineReconstruction


class ContradictionRecord(BaseModel):
    """A detected contradiction or material discrepancy between evidence sources."""
    contradiction_id: str
    case_id: str
    contradiction_type: str  # time_discrepancy | date_discrepancy | plan_vs_execution | denial_vs_claim | location_discrepancy | amount_discrepancy
    description: str
    event_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    statement_a: str
    statement_b: str
    source_a: str
    source_b: str
    unresolved_question: str
    resolution_status: str = "unresolved" # unresolved | user_clarified | dismissed


class CorroborationAnalysis(BaseModel):
    """Full cross-evidence corroboration and conflict report."""
    case_id: str
    contradictions: List[ContradictionRecord] = Field(default_factory=list)
    corroborated_event_ids: List[str] = Field(default_factory=list)
    isolated_event_ids: List[str] = Field(default_factory=list)


def are_events_same_proposition(e1: EventCandidate, e2: EventCandidate) -> bool:
    """
    Determines whether two event candidates genuinely refer to the same underlying
    activity/proposition, rather than merely sharing a common actor name or verb.
    """
    # 1. Communications sent at different times are separate messages, never the same proposition
    if e1.is_communication and e2.is_communication:
        return False

    # 2. A message sent time vs a planned event time are completely different temporal dimensions
    if (e1.timestamp_type == "message_sent_time" and e2.timestamp_type == "planned_event_time") or \
       (e2.timestamp_type == "message_sent_time" and e1.timestamp_type == "planned_event_time"):
        return False

    # 3. Document signing time vs message sent time are separate actions on different artifacts
    if (e1.timestamp_type == "document_signing_time" and e2.timestamp_type == "message_sent_time") or \
       (e2.timestamp_type == "document_signing_time" and e1.timestamp_type == "message_sent_time"):
        return False

    # 4. Check for matching specific entity references (e.g. invoice IDs, shipment IDs)
    inv_re = r"\b(?:invoice|doc|kl|id|ref|#)\s*[-:]?\s*([a-z0-9\-]+)\b"
    m1 = re.findall(inv_re, e1.description, re.IGNORECASE)
    m2 = re.findall(inv_re, e2.description, re.IGNORECASE)
    common_ids = set(m1) & set(m2)
    # Filter out generic words
    common_ids = {i.lower() for i in common_ids if len(i) > 2 and i.lower() not in {"the", "and", "for"}}
    if common_ids:
        return True

    # 5. Check for matching specific activity_name with shared actors
    act1 = (e1.activity_name or "").strip().lower()
    act2 = (e2.activity_name or "").strip().lower()
    generic_acts = {"occurred (incident)", "statement", "communication", "message sent", "occur", "event"}
    if act1 and act2 and act1 == act2 and act1 not in generic_acts:
        shared_actors = set(a.lower() for a in e1.actors) & set(a.lower() for a in e2.actors)
        if shared_actors:
            return True

    # 6. Check for matching specific locations
    if e1.location and e2.location and e1.location.strip().lower() == e2.location.strip().lower():
        # Same specific location + same event type or action
        if (e1.event_type == e2.event_type and e1.event_type in {"meeting", "delivery", "incident"}) or (e1.action.lower() == e2.action.lower() and e1.action.lower() in {"meet", "deliver", "arrive"}):
            return True

    # 7. Check for denial referring directly to the other claim
    if (e1.modality == "denied" and e2.modality != "denied") or (e2.modality == "denied" and e1.modality != "denied"):
        shared_actors = set(e1.actors) & set(e2.actors)
        if shared_actors and (e1.event_type == e2.event_type or e1.action.lower() == e2.action.lower()):
            text1 = f"{e1.title} {e1.description} {' '.join(e1.supporting_text_spans)}".lower()
            text2 = f"{e2.title} {e2.description} {' '.join(e2.supporting_text_spans)}".lower()
            words1 = set(re.findall(r"\w{3,}", text1))
            words2 = set(re.findall(r"\w{3,}", text2))
            stopwords = {"the", "and", "for", "with", "was", "will", "from"}
            if len((words1 & words2) - stopwords) >= 1:
                return True

    # 8. Check for plan vs actual occurrence of the same activity
    if (e1.modality == "planned" and e2.modality == "completed") or (e2.modality == "planned" and e1.modality == "completed"):
        if e1.event_type == e2.event_type and e1.event_type in {"meeting", "delivery"}:
            shared_actors = set(e1.actors) & set(e2.actors)
            if shared_actors:
                text1 = f"{e1.title} {e1.description} {' '.join(e1.supporting_text_spans)}".lower()
                text2 = f"{e2.title} {e2.description} {' '.join(e2.supporting_text_spans)}".lower()
                words1 = set(re.findall(r"\w{3,}", text1))
                words2 = set(re.findall(r"\w{3,}", text2))
                stopwords = {"the", "and", "for", "with", "was", "will", "from"}
                if len((words1 & words2) - stopwords) >= 1:
                    return True

    return False


def detect_time_discrepancy(e1: EventCandidate, e2: EventCandidate) -> Optional[ContradictionRecord]:
    """
    Checks if two events describing the SAME specific activity have conflicting timestamps.
    Explicitly ignores:
    - Different message timestamps in a chat / email thread.
    - Message sent times vs planned future event times.
    - Unrelated activities that happen to share a common actor.
    """
    if not e1.original_time_expression or not e2.original_time_expression:
        return None

    t1 = e1.original_time_expression.strip().lower()
    t2 = e2.original_time_expression.strip().lower()

    if t1 == t2:
        return None

    # Communications sent at different times are never a time discrepancy
    if e1.is_communication or e2.is_communication:
        return None

    # Must refer to the same underlying proposition
    if not are_events_same_proposition(e1, e2):
        return None

    # Both must be referring to the occurrence time or planned time of that same proposition
    if e1.timestamp_type != e2.timestamp_type and "unknown" not in (e1.timestamp_type, e2.timestamp_type):
        return None

    activity_name = e1.activity_name or e1.title
    return ContradictionRecord(
        contradiction_id=f"contra-time-{e1.event_id[:4]}-{e2.event_id[:4]}",
        case_id=e1.case_id,
        contradiction_type="time_discrepancy",
        description=f"Conflicting times reported for the same activity '{activity_name}': '{t1}' vs '{t2}'.",
        event_ids=[e1.event_id, e2.event_id],
        evidence_ids=list(set(e1.evidence_ids + e2.evidence_ids)),
        statement_a=e1.description,
        statement_b=e2.description,
        source_a=e1.source_segment_ids[0] if e1.source_segment_ids else "Source A",
        source_b=e2.source_segment_ids[0] if e2.source_segment_ids else "Source B",
        unresolved_question=f"Which time is accurate for {activity_name} ({t1} vs {t2})?",
    )


def detect_plan_vs_execution_or_denial(e1: EventCandidate, e2: EventCandidate) -> Optional[ContradictionRecord]:
    """
    Detects when one evidence states a plan/intent and another states a different occurrence or denial
    FOR THE SAME UNDERLYING PROPOSITION.
    """
    if not are_events_same_proposition(e1, e2):
        return None

    shared_actors = set(e1.actors) & set(e2.actors)

    is_e1_denied = e1.modality == "denied"
    is_e2_denied = e2.modality == "denied"

    if (is_e1_denied and not is_e2_denied) or (is_e2_denied and not is_e1_denied):
        activity_name = e1.activity_name or e1.title
        return ContradictionRecord(
            contradiction_id=f"contra-denial-{e1.event_id[:4]}-{e2.event_id[:4]}",
            case_id=e1.case_id,
            contradiction_type="denial_vs_claim",
            description=f"Direct denial detected regarding '{activity_name}': One source claims the event occurred while another denies it.",
            event_ids=[e1.event_id, e2.event_id],
            evidence_ids=list(set(e1.evidence_ids + e2.evidence_ids)),
            statement_a=e1.description,
            statement_b=e2.description,
            source_a=e1.source_segment_ids[0] if e1.source_segment_ids else "Source A",
            source_b=e2.source_segment_ids[0] if e2.source_segment_ids else "Source B",
            unresolved_question=f"Did {activity_name} actually occur, or was it accurately denied?",
        )

    is_e1_planned = e1.modality == "planned" or e1.explicit_or_inferred == "plan_or_promise"
    is_e2_planned = e2.modality == "planned" or e2.explicit_or_inferred == "plan_or_promise"

    if (is_e1_planned and not is_e2_planned) or (is_e2_planned and not is_e1_planned):
        if e1.original_time_expression and e2.original_time_expression and e1.original_time_expression != e2.original_time_expression:
            activity_name = e1.activity_name or e1.title
            return ContradictionRecord(
                contradiction_id=f"contra-plan-{e1.event_id[:4]}-{e2.event_id[:4]}",
                case_id=e1.case_id,
                contradiction_type="plan_vs_execution",
                description=f"Planned schedule '{e1.original_time_expression}' for '{activity_name}' diverges from reported occurrence '{e2.original_time_expression}'.",
                event_ids=[e1.event_id, e2.event_id],
                evidence_ids=list(set(e1.evidence_ids + e2.evidence_ids)),
                statement_a=e1.description,
                statement_b=e2.description,
                source_a=e1.source_segment_ids[0] if e1.source_segment_ids else "Source A",
                source_b=e2.source_segment_ids[0] if e2.source_segment_ids else "Source B",
                unresolved_question=f"Did {activity_name} take place at the planned time ({e1.original_time_expression}) or the alternative time ({e2.original_time_expression})?",
            )

    return None


def analyze_cross_evidence_relationships(
    events: List[EventCandidate],
    timeline: TimelineReconstruction,
) -> CorroborationAnalysis:
    """
    Runs cross-evidence corroboration and conflict checks across all event candidates.
    Annotates timeline entries with corroboration and contradiction flags.
    """
    contradictions: List[ContradictionRecord] = []
    corroborated_ids = set()
    isolated_ids = set()

    for i in range(len(events)):
        has_corroboration = False
        e1 = events[i]

        for j in range(i + 1, len(events)):
            e2 = events[j]

            # 1. Check for time discrepancies
            t_contra = detect_time_discrepancy(e1, e2)
            if t_contra:
                contradictions.append(t_contra)

            # 2. Check for plan vs execution / denial conflicts
            p_contra = detect_plan_vs_execution_or_denial(e1, e2)
            if p_contra:
                contradictions.append(p_contra)

            # 3. Check for genuine corroboration (independent evidence files affirming same action & actors)
            if e1.evidence_ids and e2.evidence_ids and e1.evidence_ids[0] != e2.evidence_ids[0]:
                shared_actors = set(e1.actors) & set(e2.actors)
                if shared_actors and e1.action.lower() == e2.action.lower():
                    has_corroboration = True
                    corroborated_ids.add(e1.event_id)
                    corroborated_ids.add(e2.event_id)

        if not has_corroboration and e1.event_id not in corroborated_ids:
            isolated_ids.add(e1.event_id)

    # Deduplicate contradictions by type and unresolved question
    unique_contradictions: List[ContradictionRecord] = []
    seen_keys = set()
    for c in contradictions:
        key = (c.contradiction_type, c.unresolved_question.strip().lower())
        if key not in seen_keys:
            seen_keys.add(key)
            unique_contradictions.append(c)
    contradictions = unique_contradictions

    # Annotate timeline entries
    conflicting_event_ids = set()
    for c in contradictions:
        conflicting_event_ids.update(c.event_ids)

    for entry in timeline.scheduled_events + timeline.unscheduled_events:
        if entry.event_id in conflicting_event_ids:
            entry.timeline_status = "conflicting_evidence"
            entry.contradictions = [c.model_dump() for c in contradictions if entry.event_id in c.event_ids]
        elif entry.event_id in corroborated_ids:
            entry.timeline_status = "corroborated"
        else:
            entry.timeline_status = "supported_by_evidence"

    timeline.corroborated_count = len(corroborated_ids)
    timeline.conflicting_count = len(conflicting_event_ids)

    return CorroborationAnalysis(
        case_id=timeline.case_id,
        contradictions=contradictions,
        corroborated_event_ids=list(corroborated_ids),
        isolated_event_ids=list(isolated_ids),
    )
