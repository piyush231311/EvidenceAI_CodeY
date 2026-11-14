import os
import json
import uuid
import hashlib
import tempfile
import time
from typing import List, Optional, Any, Dict
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


def run_pipeline_extraction(file_path: str, file_category: str) -> Dict[str, Any]:
    """
    Runs extraction pipeline based on file category:
    - image: PaddleOCR (PP-OCRv6 small)
    - audio: Faster-Whisper Small (lazy loaded)
    - text:  Document & Log Text Extractor
    """
    result = {
        "text": "",
        "confidence": 0.0,
        "metadata": {},
        "processing_time_ms": 0.0,
        "timestamps": [],
        "success": False,
    }

    try:
        if file_category == "image":
            from src.extraction.ocr import extract_text_from_image
            ocr_out = extract_text_from_image(file_path)
            result["text"] = ocr_out.get("text", "")
            result["confidence"] = ocr_out.get("confidence", 0.0)
            result["processing_time_ms"] = ocr_out.get("processing_time_ms", 0.0)
            result["metadata"] = {
                "lines": ocr_out.get("lines", []),
                "engine": "PaddleOCR PP-OCRv6_small",
            }
            result["success"] = True

        elif file_category == "audio":
            from src.extraction.transcription import transcribe_audio
            audio_out = transcribe_audio(file_path)
            result["text"] = audio_out.get("text", "")
            result["confidence"] = audio_out.get("language_probability", 0.0)
            result["processing_time_ms"] = audio_out.get("processing_time_ms", 0.0)
            result["timestamps"] = audio_out.get("segments", [])
            result["metadata"] = {
                "language": audio_out.get("language"),
                "duration": audio_out.get("duration"),
                "segments": audio_out.get("segments", []),
                "engine": "Faster-Whisper Small",
            }
            result["success"] = True

        elif file_category == "text":
            from src.extraction.text_extractor import extract_text_from_document
            doc_out = extract_text_from_document(file_path)
            result["text"] = doc_out.get("text", "")
            result["confidence"] = doc_out.get("confidence", 1.0)
            result["processing_time_ms"] = doc_out.get("processing_time_ms", 0.0)
            result["metadata"] = {
                "doc_metadata": doc_out.get("metadata", {}),
                "engine": "Document Text Extractor",
            }
            result["success"] = True

    except Exception as e:
        result["metadata"] = {"error": str(e)}
        result["success"] = False

    return result


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
