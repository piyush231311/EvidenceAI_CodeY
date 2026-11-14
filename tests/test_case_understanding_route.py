"""
Targeted tests for GET /api/cases/{case_id}/understanding endpoint.
Verifies:
  1. Valid understanding response for existing case 41dd7acb-1bc5-4aae-a632-afeb81537b1f.
  2. ContradictionRecord serialization without AttributeError on severity.
  3. Non-existent case returns intentional HTTP 404.
  4. Empty case returns intentional valid pending response (HTTP 200 with empty arrays).
"""

import uuid
import pytest
from fastapi import HTTPException
from backend.db import SessionLocal, init_db
from backend.models import Case, Evidence, EventRecord, EventContradictionRecord, EntityMatchRecord
from backend.routes import get_case_understanding, PreliminaryCaseUnderstandingResponse


def test_understanding_for_target_case():
    """Verifies target case 41dd7acb-1bc5-4aae-a632-afeb81537b1f returns complete understanding."""
    case_id = "41dd7acb-1bc5-4aae-a632-afeb81537b1f"
    with SessionLocal() as db:
        res = get_case_understanding(case_id, db)
        assert isinstance(res, PreliminaryCaseUnderstandingResponse)
        assert res.case_id == case_id
        assert len(res.narrative_summary) > 0
        assert len(res.established_facts) >= 5
        assert len(res.key_parties) >= 1
        assert isinstance(res.unclear_or_disputed, list)


def test_understanding_404_for_missing_case():
    """Verifies non-existent case returns HTTP 404."""
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            get_case_understanding("non-existent-case-id-99999", db)
        assert exc_info.value.status_code == 404


def test_understanding_empty_case():
    """Verifies a case with no evidence or events returns a safe, non-crashing empty response."""
    test_id = f"test-empty-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        case = Case(id=test_id)
        db.add(case)
        db.commit()

        try:
            res = get_case_understanding(test_id, db)
            assert isinstance(res, PreliminaryCaseUnderstandingResponse)
            assert res.case_id == test_id
            assert res.key_parties == []
            assert res.established_facts == []
            assert res.unclear_or_disputed == []
            assert "No evidence" in res.narrative_summary
        finally:
            db.delete(case)
            db.commit()


def test_understanding_handles_contradiction_without_severity():
    """Verifies that EventContradictionRecord without severity does not raise AttributeError."""
    test_id = f"test-contra-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        case = Case(id=test_id)
        db.add(case)

        ev = Evidence(
            id=f"ev-{uuid.uuid4().hex[:6]}",
            case_id=test_id,
            original_filename="doc.txt",
            stored_path="storage/doc.txt",
            file_type="text",
            mime_type="text/plain",
            size_bytes=100,
            sha256="dummy_hash_contra",
            extracted_text="Payment of 50000 was requested.",
        )
        db.add(ev)

        contra = EventContradictionRecord(
            id=f"contra-{uuid.uuid4().hex[:6]}",
            case_id=test_id,
            contradiction_type="amount_discrepancy",
            description="Payment amount in chat conflicts with bank slip.",
            event_ids_json="[]",
            evidence_ids_json="[]",
            statement_a="Requested 50,000",
            statement_b="Paid 25,000",
            source_a="chat.txt",
            source_b="slip.png",
            unresolved_question="Which amount is correct?",
            resolution_status="unresolved",
        )
        db.add(contra)
        db.commit()

        try:
            res = get_case_understanding(test_id, db)
            assert isinstance(res, PreliminaryCaseUnderstandingResponse)
            assert res.case_id == test_id
            assert len(res.unclear_or_disputed) >= 1
            assert "issue" in res.unclear_or_disputed[0]
        finally:
            db.delete(contra)
            db.delete(ev)
            db.delete(case)
            db.commit()
