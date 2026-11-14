import os
import json
import uuid
import hashlib
import tempfile
import time
from datetime import datetime
from typing import List, Optional, Any, Dict
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    Case, Evidence, AuditLog, EntityMatchRecord,
    EvidenceResponse, CaseResponse, AuditLogResponse,
    CandidateMatchResponse, ReviewMatchPayload, EntityMentionSchema
)
from .authenticity import run_authenticity_gate

router = APIRouter(prefix="/api", tags=["Evidence & Cases"])

# Maximum file size: 50 MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

# Allowed extensions and matching MIME types
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}
ALLOWED_AUDIO_MIMES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/m4a", "audio/x-m4a", "audio/mp4", "audio/ogg", "application/ogg"
}

ALLOWED_TEXT_EXTENSIONS = {".txt", ".json", ".csv", ".eml", ".pdf", ".docx"}
ALLOWED_TEXT_MIMES = {
    "text/plain", "application/json", "text/csv", "application/csv",
    "message/rfc822", "application/pdf", "text/x-csv", "application/octet-stream",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

STORAGE_BASE_DIR = Path("storage") / "originals"


def classify_file(filename: str, content_type: Optional[str]) -> str:
    """
    Validates file extension and MIME type.
    Returns categorized type: 'image' | 'audio' | 'text'
    Raises HTTPException if disallowed or mismatched.
    """
    ext = Path(filename).suffix.lower()
    mime = (content_type or "").lower().split(";")[0].strip()

    if ext in ALLOWED_IMAGE_EXTENSIONS:
        if mime and mime not in ALLOWED_IMAGE_MIMES and mime != "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{mime}' does not match image extension '{ext}' for file '{filename}'."
            )
        return "image"

    if ext in ALLOWED_AUDIO_EXTENSIONS:
        if mime and mime not in ALLOWED_AUDIO_MIMES and mime != "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{mime}' does not match audio extension '{ext}' for file '{filename}'."
            )
        return "audio"

    if ext in ALLOWED_TEXT_EXTENSIONS:
        if mime and mime not in ALLOWED_TEXT_MIMES and mime != "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{mime}' does not match text/document extension '{ext}' for file '{filename}'."
            )
        return "text"

    allowed_exts = sorted(list(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS | ALLOWED_TEXT_EXTENSIONS))
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported file type '{ext}' for '{filename}'. Allowed extensions: {', '.join(allowed_exts)}"
    )


def run_pipeline_extraction(file_path: str, file_category: str) -> Dict[str, Any]:
    """
    Runs unified extraction pipeline based on file category and extension.
    Uses lazy loading and singleton model caching.
    """
    try:
        from src.extraction.unified_pipeline import process_evidence
        record = process_evidence(file_path, file_category=file_category)
        return {
            "text": record.full_text,
            "confidence": record.overall_confidence,
            "metadata": record.metadata,
            "processing_time_ms": record.processing_time_ms,
            "timestamps": [s.model_dump() for s in record.segments],
            "success": record.success,
        }
    except Exception as e:
        return {
            "text": "",
            "confidence": 0.0,
            "metadata": {"error": str(e)},
            "processing_time_ms": 0.0,
            "timestamps": [],
            "success": False,
        }


@router.post("/cases/{case_id}/evidence", response_model=List[EvidenceResponse], status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str,
    files: List[UploadFile] = File(...),
    notes: Optional[str] = Form(None),
    notes_map: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload one or more evidence files for a case:
    1. Validates extension and MIME type.
    2. Validates maximum size (50 MB).
    3. Saves untouched original file to storage/originals/{case_id}/{uuid}{ext}.
    4. Computes SHA-256 hash at upload time.
    5. Runs authenticity gate check.
    6. Runs local AI extraction (PaddleOCR / Faster-Whisper / Text).
    7. Stores record in database and writes an append-only audit log entry.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided.")

    parsed_notes_map = {}
    if notes_map:
        try:
            parsed_notes_map = json.loads(notes_map)
        except Exception:
            parsed_notes_map = {}

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        case = Case(id=case_id)
        db.add(case)
        db.flush()

    case_storage_dir = STORAGE_BASE_DIR / case_id
    case_storage_dir.mkdir(parents=True, exist_ok=True)

    created_evidence: List[Evidence] = []

    for idx, upload_file in enumerate(files):
        filename = upload_file.filename or f"evidence_{idx}"
        content_type = upload_file.content_type or "application/octet-stream"

        # 1. Type & MIME validation
        file_category = classify_file(filename, content_type)

        # 2. Read content & validate size
        file_bytes = await upload_file.read()
        size_bytes = len(file_bytes)

        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' exceeds maximum allowed size of 50 MB ({size_bytes} bytes)."
            )

        # 3. Compute SHA-256 hash
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # 4. Save original file untouched with UUID
        evidence_id = str(uuid.uuid4())
        ext = Path(filename).suffix.lower()
        stored_filename = f"{evidence_id}{ext}"
        stored_path = case_storage_dir / stored_filename

        with open(stored_path, "wb") as f:
            f.write(file_bytes)

        # 5. Run authenticity gate
        auth_result = run_authenticity_gate(str(stored_path), file_category)

        # 6. Run AI Extraction (PaddleOCR / Faster-Whisper / Document)
        extraction_res = run_pipeline_extraction(str(stored_path), file_category)

        # Resolve note
        file_note = parsed_notes_map.get(filename) or notes

        # 7. Insert Evidence DB record
        evidence_record = Evidence(
            id=evidence_id,
            case_id=case_id,
            original_filename=filename,
            stored_path=str(stored_path.as_posix()),
            file_type=file_category,
            mime_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            notes=file_note,
            authenticity_passed=auth_result.get("passed", True),
            authenticity_score=auth_result.get("score"),
            extracted_text=extraction_res.get("text"),
            extraction_confidence=extraction_res.get("confidence"),
            extraction_metadata=json.dumps(extraction_res.get("metadata", {})),
            processing_time_ms=extraction_res.get("processing_time_ms"),
        )
        db.add(evidence_record)

        # 8. Write append-only audit log entry
        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case_id,
            evidence_id=evidence_id,
            action="UPLOADED_AND_EXTRACTED",
            details=json.dumps({
                "original_filename": filename,
                "file_type": file_category,
                "mime_type": content_type,
                "size_bytes": size_bytes,
                "sha256": sha256_hash,
                "stored_path": str(stored_path.as_posix()),
                "authenticity": auth_result,
                "extraction_success": extraction_res.get("success", False),
                "processing_time_ms": extraction_res.get("processing_time_ms"),
            })
        )
        db.add(audit_entry)
        created_evidence.append(evidence_record)

    db.commit()

    for item in created_evidence:
        db.refresh(item)

    return created_evidence


@router.post("/extract")
async def extract_direct(
    file: UploadFile = File(...),
):
    """
    Direct extraction endpoint for ad-hoc or testing requests:
    - Calculates SHA-256 hash from original bytes
    - Preserves file bytes during processing
    - Validates file type and size
    - Runs PaddleOCR / Faster-Whisper / Text extractor
    - Safely cleans up temporary file
    - Returns structured JSON with source ID, extraction results, confidence, timestamps, and diagnostics
    """
    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    file_category = classify_file(filename, content_type)
    file_bytes = await file.read()
    size_bytes = len(file_bytes)

    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' exceeds maximum allowed size of 50 MB ({size_bytes} bytes)."
        )

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    source_id = str(uuid.uuid4())
    ext = Path(filename).suffix.lower()

    # Save to safe temporary file for model inference
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        extraction_res = run_pipeline_extraction(tmp_path, file_category)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {
        "source_id": source_id,
        "filename": filename,
        "sha256": sha256_hash,
        "size_bytes": size_bytes,
        "file_type": file_category,
        "text": extraction_res.get("text", ""),
        "confidence": extraction_res.get("confidence", 0.0),
        "timestamps": extraction_res.get("timestamps", []),
        "metadata": extraction_res.get("metadata", {}),
        "processing_time_ms": extraction_res.get("processing_time_ms", 0.0),
        "success": extraction_res.get("success", False),
    }


@router.post("/evidence/{evidence_id}/extract", response_model=EvidenceResponse)
def trigger_evidence_extraction(evidence_id: str, db: Session = Depends(get_db)):
    """
    Trigger or re-run extraction on a stored evidence item.
    """
    record = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found.")

    file_path = Path(record.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original stored file is missing on disk.")

    ext_res = run_pipeline_extraction(str(file_path), record.file_type)

    record.extracted_text = ext_res.get("text")
    record.extraction_confidence = ext_res.get("confidence")
    record.extraction_metadata = json.dumps(ext_res.get("metadata", {}))
    record.processing_time_ms = ext_res.get("processing_time_ms")

    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        case_id=record.case_id,
        evidence_id=record.id,
        action="EXTRACTION_RECOMPUTED",
        details=json.dumps({
            "processing_time_ms": ext_res.get("processing_time_ms"),
            "confidence": ext_res.get("confidence"),
        })
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(record)
    return record


@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceResponse])
def get_case_evidence(case_id: str, db: Session = Depends(get_db)):
    """
    Returns all evidence records for the specified case, ordered chronologically.
    """
    evidence_items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.uploaded_at.desc())
        .all()
    )
    return evidence_items


@router.get("/evidence/{evidence_id}/file")
def stream_evidence_file(evidence_id: str, db: Session = Depends(get_db)):
    """
    Streams back the original untouched file from local storage.
    """
    record = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found.")

    file_path = Path(record.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original stored file is missing on disk.")

    return FileResponse(
        path=str(file_path),
        media_type=record.mime_type,
        filename=record.original_filename
    )


@router.get("/cases/{case_id}/audit-logs", response_model=List[AuditLogResponse])
def get_case_audit_logs(case_id: str, db: Session = Depends(get_db)):
    """
    Returns append-only audit log entries for a case to verify forensic traceability.
    """
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )
    result = []
    for log in logs:
        details_obj = None
        if log.details:
            try:
                details_obj = json.loads(log.details)
            except Exception:
                details_obj = log.details
        result.append(AuditLogResponse(
            id=log.id,
            case_id=log.case_id,
            evidence_id=log.evidence_id,
            action=log.action,
            timestamp=log.timestamp,
            details=details_obj
        ))
    return result


@router.get("/cases", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    """List all cases."""
    return db.query(Case).order_by(Case.created_at.desc()).all()


class CreateCasePayload(BaseModel):
    id: Optional[str] = None


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(payload: Optional[CreateCasePayload] = None, db: Session = Depends(get_db)):
    """Create a new case with an optional specified ID or auto-generated UUID."""
    case_id = (payload.id.strip() if payload and payload.id else None) or str(uuid.uuid4())
    existing = db.query(Case).filter(Case.id == case_id).first()
    if existing:
        return existing
    case = Case(id=case_id)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: str, db: Session = Depends(get_db)):
    """Delete a case and its associated evidence."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    db.delete(case)
    db.commit()
    return None


@router.get("/evidence", response_model=List[EvidenceResponse])
def list_all_evidence(db: Session = Depends(get_db)):
    """List all evidence across cases."""
    return db.query(Evidence).order_by(Evidence.uploaded_at.desc()).all()


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """Delete an evidence record."""
    item = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found.")
    db.delete(item)
    db.commit()
    return None


@router.post("/cases/{case_id}/extract-all", response_model=List[EvidenceResponse])
def extract_all_case_evidence(case_id: str, db: Session = Depends(get_db)):
    """
    Trigger extraction across all evidence items in a case.
    Reuses existing extracted results unless empty.
    """
    items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    if not items:
        return []

    updated_items = []
    for record in items:
        file_path = Path(record.stored_path)
        if not file_path.exists():
            continue

        ext_res = run_pipeline_extraction(str(file_path), record.file_type)
        record.extracted_text = ext_res.get("text")
        record.extraction_confidence = ext_res.get("confidence")
        record.extraction_metadata = json.dumps(ext_res.get("metadata", {}))
        record.processing_time_ms = ext_res.get("processing_time_ms")

        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            case_id=record.case_id,
            evidence_id=record.id,
            action="EXTRACTION_COMPUTED",
            details=json.dumps({
                "processing_time_ms": ext_res.get("processing_time_ms"),
                "confidence": ext_res.get("confidence"),
                "file_type": record.file_type,
            })
        )
        db.add(audit_entry)
        updated_items.append(record)

    db.commit()
    for item in updated_items:
        db.refresh(item)
    return updated_items


@router.post("/cases/{case_id}/entities/match", response_model=List[CandidateMatchResponse])
def run_case_entity_matching(case_id: str, db: Session = Depends(get_db)):
    """
    Runs GLiNER entity extraction on all case evidence text, then uses RapidFuzz
    to propose cross-evidence candidate entity matches for human review.
    """
    evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    if not evidence_items:
        return []

    # Ensure evidence has extracted text
    from src.intelligence.gliner_extractor import extract_entities_from_text, ExtractedEntity
    from src.intelligence.entity_matcher import generate_candidate_matches

    all_entities: List[ExtractedEntity] = []

    for ev in evidence_items:
        # Run extraction if text is not already present
        if not ev.extracted_text:
            file_path = Path(ev.stored_path)
            if file_path.exists():
                ext_res = run_pipeline_extraction(str(file_path), ev.file_type)
                ev.extracted_text = ext_res.get("text")
                ev.extraction_confidence = ext_res.get("confidence")
                ev.extraction_metadata = json.dumps(ext_res.get("metadata", {}))
                ev.processing_time_ms = ext_res.get("processing_time_ms")
                db.flush()

        if ev.extracted_text and ev.extracted_text.strip():
            ents = extract_entities_from_text(
                ev.extracted_text,
                evidence_id=ev.id,
                filename=ev.original_filename,
            )
            all_entities.extend(ents)

    # Generate candidate matches across all evidence
    candidate_matches = generate_candidate_matches(all_entities, case_id=case_id)

    # Fetch existing confirmed/rejected statuses to preserve user reviews
    existing_records = {
        (rec.entity_type, rec.canonical_name): rec
        for rec in db.query(EntityMatchRecord).filter(EntityMatchRecord.case_id == case_id).all()
    }

    response_list: List[CandidateMatchResponse] = []

    for cand in candidate_matches:
        key = (cand.entity_type, cand.canonical_name)
        existing = existing_records.get(key)

        mentions_data = [m.model_dump() for m in cand.mentions]

        if existing:
            # Preserve existing user decision if already reviewed
            cand_id = existing.id
            cand_status = existing.status
            reviewed_at = existing.reviewed_at
            review_notes = existing.review_notes
            # Update mentions and score
            existing.mentions_json = json.dumps(mentions_data)
            existing.similarity_score = cand.similarity_score
        else:
            cand_id = cand.match_id
            cand_status = "pending"
            reviewed_at = None
            review_notes = None

            new_rec = EntityMatchRecord(
                id=cand_id,
                case_id=case_id,
                entity_type=cand.entity_type,
                canonical_name=cand.canonical_name,
                similarity_score=cand.similarity_score,
                status=cand_status,
                mentions_json=json.dumps(mentions_data),
            )
            db.add(new_rec)

        response_list.append(
            CandidateMatchResponse(
                id=cand_id,
                case_id=case_id,
                entity_type=cand.entity_type,
                canonical_name=cand.canonical_name,
                similarity_score=cand.similarity_score,
                status=cand_status,
                mentions=[EntityMentionSchema(**m) for m in mentions_data],
                created_at=cand.created_at,
                reviewed_at=reviewed_at,
                review_notes=review_notes,
            )
        )

    # Audit log
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        case_id=case_id,
        action="ENTITY_MATCHING_COMPUTED",
        details=json.dumps({
            "total_entities_extracted": len(all_entities),
            "candidate_matches_count": len(response_list),
        }),
    )
    db.add(audit_entry)
    db.commit()

    return response_list


@router.get("/cases/{case_id}/entities", response_model=List[CandidateMatchResponse])
def get_case_entities(case_id: str, db: Session = Depends(get_db)):
    """
    Returns stored candidate entity matches for a case.
    """
    records = (
        db.query(EntityMatchRecord)
        .filter(EntityMatchRecord.case_id == case_id)
        .order_by(EntityMatchRecord.created_at.desc())
        .all()
    )

    result = []
    for rec in records:
        try:
            mentions_list = json.loads(rec.mentions_json)
        except Exception:
            mentions_list = []

        result.append(
            CandidateMatchResponse(
                id=rec.id,
                case_id=rec.case_id,
                entity_type=rec.entity_type,
                canonical_name=rec.canonical_name,
                similarity_score=rec.similarity_score,
                status=rec.status,
                mentions=[EntityMentionSchema(**m) for m in mentions_list],
                created_at=rec.created_at,
                reviewed_at=rec.reviewed_at,
                review_notes=rec.review_notes,
            )
        )
    return result


@router.post("/entities/matches/{match_id}/review", response_model=CandidateMatchResponse)
def review_entity_match(
    match_id: str,
    payload: ReviewMatchPayload,
    db: Session = Depends(get_db)
):
    """
    Allows a human investigator to confirm, reject, or mark as separate
    a candidate entity match, recording a forensic audit log entry.
    """
    valid_actions = {"confirm", "reject", "separate", "undo"}
    if payload.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{payload.action}'. Must be one of: {', '.join(sorted(valid_actions))}"
        )

    match_rec = db.query(EntityMatchRecord).filter(EntityMatchRecord.id == match_id).first()
    if not match_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity match not found.")

    status_map = {
        "confirm": "confirmed",
        "reject": "rejected",
        "separate": "separate",
        "undo": "pending",
    }
    match_rec.status = status_map[payload.action]
    match_rec.reviewed_at = datetime.utcnow() if payload.action != "undo" else None
    if payload.review_notes is not None:
        match_rec.review_notes = payload.review_notes

    # Add audit log
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        case_id=match_rec.case_id,
        action=f"ENTITY_REVIEW_{payload.action.upper()}",
        details=json.dumps({
            "match_id": match_id,
            "canonical_name": match_rec.canonical_name,
            "entity_type": match_rec.entity_type,
            "status": match_rec.status,
            "notes": payload.review_notes,
        }),
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(match_rec)

    try:
        mentions_list = json.loads(match_rec.mentions_json)
    except Exception:
        mentions_list = []

    return CandidateMatchResponse(
        id=match_rec.id,
        case_id=match_rec.case_id,
        entity_type=match_rec.entity_type,
        canonical_name=match_rec.canonical_name,
        similarity_score=match_rec.similarity_score,
        status=match_rec.status,
        mentions=[EntityMentionSchema(**m) for m in mentions_list],
        created_at=match_rec.created_at,
        reviewed_at=match_rec.reviewed_at,
        review_notes=match_rec.review_notes,
    )


