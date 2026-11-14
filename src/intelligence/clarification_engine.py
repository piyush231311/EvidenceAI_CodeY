"""
Interactive User Clarification & Surety Assessment Engine for Evidence AI.

Generates focused, non-leading questions targeting real unresolved uncertainties discovered
during timeline construction and contradiction analysis.
Presents a synthesized "What we understand so far" preliminary case understanding before the quiz.
Incorporates user surety ratings and knowledge basis without overwriting objective documentary evidence.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.intelligence.evidence_reasoner import ContradictionRecord
from src.intelligence.timeline_builder import TimelineReconstruction, TimelineEntry


# Ordinal surety mapping: ordinal review weights, NOT probabilities of objective truth
SURETY_MAPPING = {
    "Very sure": 4,
    "Fairly sure": 3,
    "Somewhat sure": 2,
    "Unsure": 1,
    "Do not remember": 0,
}

KNOWLEDGE_BASIS_OPTIONS = [
    "Not specified",
    "Directly witnessed",
    "Personally participated",
    "Told by someone else",
    "Inferred",
    "Unknown",
]


class PreliminaryCaseUnderstanding(BaseModel):
    """Synthesized preliminary understanding of case evidence before clarification."""
    case_id: str
    case_domain: str = "general_investigation"
    narrative_summary: str
    what_happened: str = ""
    what_remains_unclear: List[str] = Field(default_factory=list)
    what_would_help: List[str] = Field(default_factory=list)
    key_parties: List[Dict[str, Any]] = Field(default_factory=list)
    established_facts: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_or_planned: List[Dict[str, Any]] = Field(default_factory=list)
    claims_and_allegations: List[Dict[str, Any]] = Field(default_factory=list)
    unclear_or_disputed: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_sources: List[Dict[str, Any]] = Field(default_factory=list)


class ClarificationQuestion(BaseModel):
    """A focused clarification questionnaire item derived from case uncertainties."""
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    event_id: Optional[str] = None
    contradiction_id: Optional[str] = None
    question_type: str  # timestamp_conflict | missing_time | plan_vs_actual | person_identity | location_dispute | contextual
    activity_name: str = ""
    prompt: str
    why_it_matters: str = ""
    context_excerpt: str
    options: List[str] = Field(default_factory=list)
    priority: int = 1
    status: str = "unanswered"  # unanswered | answered | dismissed
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserAnswer(BaseModel):
    """Investigator or witness response to a clarification question."""
    answer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_id: str
    case_id: str
    event_id: Optional[str] = None
    selected_option: str
    free_text_clarification: Optional[str] = None
    user_surety: str = "Fairly sure"  # Very sure | Fairly sure | Somewhat sure | Unsure | Do not remember
    surety_score: int = 3             # 0 - 4 ordinal rating
    knowledge_basis: str = "Not specified"  # Default: Not specified (never assume directly witnessed)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


def generate_preliminary_case_understanding(
    case_id: str,
    evidence_files: List[Any],
    events: List[Any],
    contradictions: List[ContradictionRecord],
    entities: Optional[List[Any]] = None,
    timeline: Optional[TimelineReconstruction] = None,
    user_answers: Optional[List[UserAnswer]] = None,
) -> PreliminaryCaseUnderstanding:
    """
    Synthesizes a transparent preliminary case understanding before asking questions.
    Uses the rich case understanding engine for natural narrative and 3-section layout.
    """
    from src.intelligence.case_understanding import generate_case_understanding
    from src.intelligence.timeline_builder import build_timeline_from_events

    tl = timeline or build_timeline_from_events(events, case_id=case_id)
    cu = generate_case_understanding(
        case_id=case_id,
        evidence_files=evidence_files,
        events=events,
        timeline=tl,
        contradictions=contradictions,
        user_answers=user_answers,
    )

    # 1. Summarize Evidence Sources
    sources_summary = []
    file_map = {}
    for ef in evidence_files:
        ef_id = getattr(ef, "id", None) or getattr(ef, "evidence_id", "")
        filename = getattr(ef, "filename", "") or getattr(ef, "title", "Evidence File") or getattr(ef, "original_filename", "Evidence File")
        file_type = getattr(ef, "file_type", "") or getattr(ef, "mime_type", "document")
        file_map[ef_id] = filename
        sources_summary.append({
            "evidence_id": ef_id,
            "filename": filename,
            "file_type": file_type,
        })

    # 2. Key Parties
    key_parties = [{"name": p, "entity_type": "PARTICIPANT", "mentions": 1, "sources": []} for p in cu.key_participants]

    # 3. Established facts vs proposed
    established_facts = []
    proposed_or_planned = []
    for ev in events:
        st = getattr(ev, "event_status", "observed")
        title = getattr(ev, "title", "Event")
        raw_time = getattr(ev, "original_time_expression", "") or "Undated"
        ev_id = getattr(ev, "evidence_id", "") or (ev.evidence_ids[0] if getattr(ev, "evidence_ids", None) else "")
        ev_title = file_map.get(ev_id, "Document")

        if st in ("proposed", "planned"):
            proposed_or_planned.append({
                "activity": getattr(ev, "activity_name", title),
                "proposed_time": raw_time,
                "status": "Unconfirmed proposal",
                "evidence_title": ev_title,
                "evidence_id": ev_id,
            })
        else:
            established_facts.append({
                "fact_statement": title,
                "timestamp": raw_time,
                "evidence_title": ev_title,
                "evidence_id": ev_id,
            })

    unclear_items = [{"issue": u} for u in cu.what_remains_unclear]

    return PreliminaryCaseUnderstanding(
        case_id=case_id,
        case_domain=cu.case_domain,
        narrative_summary=cu.what_happened,
        what_happened=cu.what_happened,
        what_remains_unclear=cu.what_remains_unclear,
        what_would_help=cu.what_would_help,
        key_parties=key_parties,
        established_facts=established_facts[:12],
        proposed_or_planned=proposed_or_planned[:8],
        claims_and_allegations=[],
        unclear_or_disputed=unclear_items,
        evidence_sources=sources_summary,
    )


def generate_clarification_quiz(
    case_id: str,
    contradictions: List[ContradictionRecord],
    timeline: TimelineReconstruction,
    max_questions: int = 5,
    evidence_files: Optional[List[Any]] = None,
    events: Optional[List[Any]] = None,
) -> List[ClarificationQuestion]:
    """
    Constructs a focused, human-readable contextual clarification quiz.
    Generates story-grounded questions targeting genuine case uncertainties:
    - Banking/KYC: OTP disclosure, unrecognized Jiffy Wallet debits, SMS link interaction.
    - Corporate/Invoice: Proposed meeting execution, invoice verification authenticity, loan vs benefit.
    """
    from src.intelligence.case_understanding import generate_case_understanding

    ev_files = evidence_files or []
    ev_candidates = events or []

    cu = generate_case_understanding(
        case_id=case_id,
        evidence_files=ev_files,
        events=ev_candidates,
        timeline=timeline,
        contradictions=contradictions,
    )

    questions: List[ClarificationQuestion] = []
    seen_prompts = set()

    # Prioritize contextual questions derived from case understanding
    for q in cu.contextual_questions:
        if len(questions) >= max_questions:
            break
        if q.prompt not in seen_prompts:
            seen_prompts.add(q.prompt)
            # Ensure "I don't know" option is always present
            opts = list(q.options)
            if not any("not sure" in o.lower() or "don't know" in o.lower() or "not recall" in o.lower() or "unsure" in o.lower() for o in opts):
                opts.append("I do not know / Not sure")
            if not any("witness" in o.lower() for o in opts):
                opts.append("I did not personally witness this")
            q.options = opts
            questions.append(q)

    # If additional questions needed, add from genuine contradictions
    for c in contradictions:
        if len(questions) >= max_questions:
            break
        activity = c.unresolved_question or "this activity"
        if activity.startswith("Which time account is accurate for: "):
            activity = activity[len("Which time account is accurate for: "):]

        prompt = f"Evidence records show conflicting information regarding {activity}. Can you clarify which account is accurate?"
        if prompt not in seen_prompts:
            seen_prompts.add(prompt)
            questions.append(
                ClarificationQuestion(
                    case_id=case_id,
                    contradiction_id=c.contradiction_id,
                    question_type=c.contradiction_type,
                    activity_name=activity,
                    prompt=prompt,
                    why_it_matters=f"Resolving {activity} establishes the accurate sequence of occurrences.",
                    context_excerpt=f"Source A: \"{c.statement_a}\"\nSource B: \"{c.statement_b}\"",
                    options=[
                        f"Account A is accurate: '{c.statement_a[:60]}...'",
                        f"Account B is accurate: '{c.statement_b[:60]}...'",
                        "Neither account is accurate",
                        "I do not know / Not sure",
                        "I did not personally witness this",
                    ],
                    priority=2,
                )
            )

    return questions


def apply_clarifications_to_timeline(
    timeline: TimelineReconstruction,
    answers: List[UserAnswer],
    questions_map: Dict[str, ClarificationQuestion],
) -> TimelineReconstruction:
    """
    Iterative reconstruction:
    Merges user clarification responses into the timeline view.
    Maintains transparency: never deletes contradictory documentary evidence or claims fake certainty.
    """
    answers_by_event: Dict[str, List[UserAnswer]] = {}
    for a in answers:
        if a.event_id:
            answers_by_event.setdefault(a.event_id, []).append(a)

    for entry in timeline.scheduled_events + timeline.unscheduled_events:
        event_answers = answers_by_event.get(entry.event_id, [])
        if event_answers:
            latest_ans = max(event_answers, key=lambda a: a.submitted_at)
            entry.timeline_status = "user_reported" if entry.timeline_status != "conflicting_evidence" else "conflicting_evidence"
            entry.description += (
                f"\n[User Clarification: '{latest_ans.selected_option}' "
                f"(Surety: {latest_ans.user_surety}, Basis: {latest_ans.knowledge_basis})]"
            )

    return timeline
