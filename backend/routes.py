import os
import json
import uuid
import hashlib
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .db import get_db
from .models import Case, Evidence, AuditLog, EvidenceResponse, CaseResponse, AuditLogResponse
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

ALLOWED_TEXT_EXTENSIONS = {".txt", ".json", ".csv", ".eml", ".pdf"}
ALLOWED_TEXT_MIMES = {
    "text/plain", "application/json", "text/csv", "application/csv",
    "message/rfc822", "application/pdf", "text/x-csv", "application/octet-stream"
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
    6. Stores record in database and writes an append-only audit log entry.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided.")

    # Parse per-file notes mapping if supplied as JSON, otherwise fallback to single note
    parsed_notes_map = {}
    if notes_map:
        try:
            parsed_notes_map = json.loads(notes_map)
        except Exception:
            parsed_notes_map = {}

    # Ensure case exists or create it
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        case = Case(id=case_id)
        db.add(case)
        db.flush()

    # Target storage directory for this case
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

        # Resolve note for this specific file
        file_note = parsed_notes_map.get(filename) or notes

        # 6. Insert Evidence DB record
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
        )
        db.add(evidence_record)

        # 7. Write append-only audit log entry
        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case_id,
            evidence_id=evidence_id,
            action="UPLOADED",
            details=json.dumps({
                "original_filename": filename,
                "file_type": file_category,
                "mime_type": content_type,
                "size_bytes": size_bytes,
                "sha256": sha256_hash,
                "stored_path": str(stored_path.as_posix()),
                "authenticity": auth_result
            })
        )
        db.add(audit_entry)
        created_evidence.append(evidence_record)

    db.commit()

    for item in created_evidence:
        db.refresh(item)

    return created_evidence


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
    # Parse JSON details if string
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
