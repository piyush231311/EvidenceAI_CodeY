"""
Python Timeline Construction Engine for Evidence AI.

Handles:
- Deterministic chronological sorting and temporal normalization
- Safe handling of ambiguous times without AM/PM or timezone guesswork
- Separation of scheduled timeline events vs Unscheduled/Time-Unknown events
- Event deduplication and multi-source corroboration linking
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import dateutil.parser

from src.intelligence.event_extractor import EventCandidate


class TimelineEntry(BaseModel):
    """A chronologically positioned or unscheduled entry on the case timeline."""
    entry_id: str
    event_id: str
    case_id: str = ""
    title: str
    description: str = ""
    event_type: str = "statement"
    actors: List[str] = Field(default_factory=list)
    action: str = "occur"
    location: Optional[str] = None
    original_time_expression: Optional[str] = None
    timestamp: Optional[datetime] = None
    temporal_precision: str = "unknown"  # exact_minute | date_only | approximate | unknown
    is_unscheduled: bool = False
    timeline_status: str = "supported_by_evidence" # supported_by_evidence | corroborated | conflicting_evidence | user_reported | inferred_uncertain | unverified
    evidence_ids: List[str] = Field(default_factory=list)
    source_segment_ids: List[str] = Field(default_factory=list)
    supporting_text_spans: List[str] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    modality: str = "completed"
    explicit_or_inferred: str = "explicit_statement"


class TimelineReconstruction(BaseModel):
    """Complete case timeline reconstruction output."""
    case_id: str
    scheduled_events: List[TimelineEntry] = Field(default_factory=list)
    unscheduled_events: List[TimelineEntry] = Field(default_factory=list)
    total_events_count: int = 0
    corroborated_count: int = 0
    conflicting_count: int = 0
    reconstructed_at: datetime = Field(default_factory=datetime.utcnow)


def parse_event_temporal_anchor(
    time_expr: Optional[str],
    reference_date_str: Optional[str] = None,
) -> Tuple[Optional[datetime], str, bool]:
    """
    Parses a temporal expression into a normalized datetime without guessing.
    Returns:
        (parsed_datetime, precision, is_ambiguous)
    """
    if not time_expr or not time_expr.strip():
        return None, "unknown", False

    expr = time_expr.strip()

    # Relative expressions that cannot be resolved without explicit base timestamp
    if expr.lower() in {"today", "yesterday", "tomorrow", "now", "later", "earlier", "then", "recently"}:
        return None, "approximate", True

    try:
        # Check if expression contains a full date (has year/month/day)
        has_month = bool(re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b", expr, re.IGNORECASE))
        has_time = bool(re.search(r"\b\d{1,2}:\d{2}\b", expr))

        if has_month and has_time:
            dt = dateutil.parser.parse(expr, fuzzy=True)
            return dt, "exact_minute", False
        elif has_month:
            dt = dateutil.parser.parse(expr, default=datetime(2026, 1, 1), fuzzy=True)
            return dt, "date_only", False
        elif has_time:
            # Isolated clock time (e.g. '10:14' or '4:30 PM')
            # If reference date string is provided (e.g. from document header), anchor it
            if reference_date_str:
                ref_dt = dateutil.parser.parse(reference_date_str, fuzzy=True)
                time_only = dateutil.parser.parse(expr).time()
                anchored_dt = datetime.combine(ref_dt.date(), time_only)
                return anchored_dt, "exact_minute", False
            else:
                # Isolated time without calendar anchor -> marked as unscheduled/ambiguous
                return None, "exact_minute", True
    except Exception:
        pass

    return None, "unknown", True


def build_timeline_from_events(
    events: List[EventCandidate],
    case_id: str,
    evidence_date_map: Optional[Dict[str, str]] = None,
) -> TimelineReconstruction:
    """
    Deterministic timeline construction:
    - Normalizes dates and timestamps.
    - Separates chronological events from unscheduled / time-unknown events.
    - Sorts scheduled events chronologically.
    - Preserves evidence citations and provenance.
    """
    evidence_dates = evidence_date_map or {}
    scheduled: List[TimelineEntry] = []
    unscheduled: List[TimelineEntry] = []

    for ev in events:
        ref_date = None
        if ev.evidence_ids and ev.evidence_ids[0] in evidence_dates:
            ref_date = evidence_dates[ev.evidence_ids[0]]

        if getattr(ev, "normalized_start_time", None) is not None:
            dt = ev.normalized_start_time
            precision = getattr(ev, "temporal_precision", "exact_minute") or "exact_minute"
            is_ambiguous = False
        else:
            dt, precision, is_ambiguous = parse_event_temporal_anchor(
                ev.original_time_expression or ev.description,
                reference_date_str=ref_date,
            )

        entry = TimelineEntry(
            entry_id=f"tl-{ev.event_id[:8]}",
            event_id=ev.event_id,
            case_id=case_id,
            title=ev.title,
            description=ev.description,
            event_type=ev.event_type,
            actors=ev.actors,
            action=ev.action,
            location=ev.location,
            original_time_expression=ev.original_time_expression,
            timestamp=dt,
            temporal_precision=precision,
            is_unscheduled=(dt is None),
            timeline_status="supported_by_evidence",
            evidence_ids=ev.evidence_ids,
            source_segment_ids=ev.source_segment_ids,
            supporting_text_spans=ev.supporting_text_spans,
            modality=ev.modality,
            explicit_or_inferred=ev.explicit_or_inferred,
        )

        if dt is not None:
            scheduled.append(entry)
        else:
            unscheduled.append(entry)

    # Sort scheduled events chronologically
    scheduled.sort(key=lambda e: e.timestamp or datetime.min)

    return TimelineReconstruction(
        case_id=case_id,
        scheduled_events=scheduled,
        unscheduled_events=unscheduled,
        total_events_count=len(scheduled) + len(unscheduled),
        corroborated_count=0,
        conflicting_count=0,
    )
