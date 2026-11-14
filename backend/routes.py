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
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    User, UserSession, UserResponse, LoginPayload, AuthStatusResponse, DemoCredentialsResponse,
    Case, Evidence, AuditLog, EntityMatchRecord,
    EventRecord, EventContradictionRecord, ClarificationQuestionRecord,
    UserAnswerRecord, ReconstructedReportRecord, MVPAnalysisRecord,
    AnalysisJobRecord, AnalysisStageRecord,
    EvidenceResponse, CaseResponse, AuditLogResponse,
    CandidateMatchResponse, ReviewMatchPayload, EntityMentionSchema,
    EventCandidateResponse, TimelineEntryResponse, TimelineResponse,
    ContradictionResponse, ClarificationQuestionResponse,
    SubmitAnswerPayload, UserAnswerResponse, ReportResponse,
    PreliminaryCaseUnderstandingResponse, MVPCaseAnalysisResponse,
    AnalysisStageResponse, AnalysisJobResponse
)
from .authenticity import run_authenticity_gate
from .auth import (
    hash_password, verify_password, create_user_session, invalidate_user_session,
    get_current_user, get_current_user_optional, SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
)

router = APIRouter(prefix="/api", tags=["Evidence & Cases"])


def check_case_access(case: Optional[Case], user: Optional[User] = None) -> Case:
    """Verifies that the requested case exists and belongs to the authenticated user."""
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if isinstance(user, User):
        if case.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return case


# =====================================================================
# AUTHENTICATION ENDPOINTS
# =====================================================================

@router.post("/auth/login")
def login(payload: LoginPayload, response: Response, db: Session = Depends(get_db)):
    """Authenticate with email and password, setting an HTTP-only session cookie."""
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    session = create_user_session(db, user.id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/"
    )
    return {
        "authenticated": True,
        "token": session.id,
        "user": UserResponse.model_validate(user)
    }


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Invalidate session and clear HTTP-only cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        invalidate_user_session(db, token)

    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user profile."""
    return {
        "authenticated": True,
        "user": UserResponse.model_validate(current_user)
    }


@router.get("/auth/demo-credentials")
def get_demo_credentials():
    """Return public demo credentials if running in development mode."""
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        return {
            "enabled": False,
            "email": "",
            "password": ""
        }
    return {
        "enabled": True,
        "email": "demo@evidenceai.local",
        "password": "DemoUser123!"
    }


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        owner_id = current_user.id if isinstance(current_user, User) else None
        case = Case(id=case_id, owner_id=owner_id)
        db.add(case)
        db.flush()
    else:
        check_case_access(case, current_user)

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
    current_user: User = Depends(get_current_user)
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
    case = db.query(Case).filter(Case.id == record.case_id).first()
    check_case_access(case, current_user)

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
def get_case_evidence(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns all evidence records for the specified case, ordered chronologically.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    check_case_access(case, current_user)
    evidence_items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.uploaded_at.desc())
        .all()
    )
    return evidence_items


@router.get("/evidence/{evidence_id}/file")
def stream_evidence_file(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Streams back the original untouched file from local storage.
    """
    record = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found.")
    case = db.query(Case).filter(Case.id == record.case_id).first()
    check_case_access(case, current_user)

    file_path = Path(record.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original stored file is missing on disk.")

    return FileResponse(
        path=str(file_path),
        media_type=record.mime_type,
        filename=record.original_filename
    )


@router.get("/cases/{case_id}/audit-logs", response_model=List[AuditLogResponse])
def get_case_audit_logs(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
def list_cases(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List cases owned by the authenticated user."""
    if isinstance(current_user, User):
        return db.query(Case).filter(Case.owner_id == current_user.id).order_by(Case.created_at.desc()).all()
    return db.query(Case).order_by(Case.created_at.desc()).all()


class CreateCasePayload(BaseModel):
    id: Optional[str] = None


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: Optional[CreateCasePayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new case with an optional specified ID or auto-generated UUID for the authenticated user."""
    case_id = (payload.id.strip() if payload and payload.id else None) or str(uuid.uuid4())
    existing = db.query(Case).filter(Case.id == case_id).first()
    if existing:
        if isinstance(current_user, User) and existing.owner_id and existing.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case already exists under another owner.")
        return existing
    owner_id = current_user.id if isinstance(current_user, User) else None
    case = Case(id=case_id, owner_id=owner_id)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a case and its associated evidence."""
    case = db.query(Case).filter(Case.id == case_id).first()
    check_case_access(case, current_user)
    db.delete(case)
    db.commit()
    return None


@router.get("/evidence", response_model=List[EvidenceResponse])
def list_all_evidence(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all evidence across cases owned by the authenticated user."""
    if isinstance(current_user, User):
        return (
            db.query(Evidence)
            .join(Case, Evidence.case_id == Case.id)
            .filter(Case.owner_id == current_user.id)
            .order_by(Evidence.uploaded_at.desc())
            .all()
        )
    return db.query(Evidence).order_by(Evidence.uploaded_at.desc()).all()


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete an evidence record."""
    item = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found.")
    case = db.query(Case).filter(Case.id == item.case_id).first()
    check_case_access(case, current_user)
    db.delete(item)
    db.commit()
    return None


@router.post("/cases/{case_id}/extract-all", response_model=List[EvidenceResponse])
def extract_all_case_evidence(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
                ocr_confidence=ev.extraction_confidence,
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
            existing.classification_confidence = cand.classification_confidence
            existing.ocr_confidence = cand.ocr_confidence
            existing.extraction_confidence = cand.extraction_confidence
            existing.is_single_occurrence = cand.is_single_occurrence
            existing.is_low_confidence = cand.is_low_confidence
            existing.requires_source_verification = cand.requires_source_verification
            existing.verification_reasons_json = json.dumps(cand.verification_reasons)
            existing.related_entities_json = json.dumps(cand.related_entities)
            existing.match_type = cand.match_type
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
                classification_confidence=cand.classification_confidence,
                ocr_confidence=cand.ocr_confidence,
                extraction_confidence=cand.extraction_confidence,
                is_single_occurrence=cand.is_single_occurrence,
                is_low_confidence=cand.is_low_confidence,
                requires_source_verification=cand.requires_source_verification,
                verification_reasons_json=json.dumps(cand.verification_reasons),
                related_entities_json=json.dumps(cand.related_entities),
                match_type=cand.match_type,
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
                classification_confidence=cand.classification_confidence,
                ocr_confidence=cand.ocr_confidence,
                extraction_confidence=cand.extraction_confidence,
                is_single_occurrence=cand.is_single_occurrence,
                is_low_confidence=cand.is_low_confidence,
                requires_source_verification=cand.requires_source_verification,
                verification_reasons=cand.verification_reasons,
                related_entities=cand.related_entities,
                match_type=cand.match_type,
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
def get_case_entities(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

        reasons = []
        if getattr(rec, "verification_reasons_json", None):
            try:
                reasons = json.loads(rec.verification_reasons_json)
            except Exception:
                reasons = []

        related = []
        if getattr(rec, "related_entities_json", None):
            try:
                related = json.loads(rec.related_entities_json)
            except Exception:
                related = []

        result.append(
            CandidateMatchResponse(
                id=rec.id,
                case_id=rec.case_id,
                entity_type=rec.entity_type,
                canonical_name=rec.canonical_name,
                similarity_score=rec.similarity_score,
                classification_confidence=rec.classification_confidence if getattr(rec, "classification_confidence", None) is not None else 1.0,
                ocr_confidence=getattr(rec, "ocr_confidence", None),
                extraction_confidence=rec.extraction_confidence if rec.extraction_confidence is not None else 1.0,
                is_single_occurrence=rec.is_single_occurrence if rec.is_single_occurrence is not None else False,
                is_low_confidence=rec.is_low_confidence if getattr(rec, "is_low_confidence", None) is not None else False,
                requires_source_verification=rec.requires_source_verification if getattr(rec, "requires_source_verification", None) is not None else False,
                verification_reasons=reasons,
                related_entities=related,
                match_type=rec.match_type,
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

    reasons = []
    if getattr(match_rec, "verification_reasons_json", None):
        try:
            reasons = json.loads(match_rec.verification_reasons_json)
        except Exception:
            reasons = []

    related = []
    if getattr(match_rec, "related_entities_json", None):
        try:
            related = json.loads(match_rec.related_entities_json)
        except Exception:
            related = []

    return CandidateMatchResponse(
        id=match_rec.id,
        case_id=match_rec.case_id,
        entity_type=match_rec.entity_type,
        canonical_name=match_rec.canonical_name,
        similarity_score=match_rec.similarity_score,
        classification_confidence=match_rec.classification_confidence if getattr(match_rec, "classification_confidence", None) is not None else 1.0,
        ocr_confidence=getattr(match_rec, "ocr_confidence", None),
        extraction_confidence=match_rec.extraction_confidence if match_rec.extraction_confidence is not None else 1.0,
        is_single_occurrence=match_rec.is_single_occurrence if match_rec.is_single_occurrence is not None else False,
        is_low_confidence=match_rec.is_low_confidence if getattr(match_rec, "is_low_confidence", None) is not None else False,
        requires_source_verification=match_rec.requires_source_verification if getattr(match_rec, "requires_source_verification", None) is not None else False,
        verification_reasons=reasons,
        related_entities=related,
        match_type=match_rec.match_type,
        status=match_rec.status,
        mentions=[EntityMentionSchema(**m) for m in mentions_list],
        created_at=match_rec.created_at,
        reviewed_at=match_rec.reviewed_at,
        review_notes=match_rec.review_notes,
    )


# =====================================================================
# QWEN EVENT EXTRACTION, TIMELINE, CONTRADICTIONS, QUIZ & REPORTING
# =====================================================================

@router.get("/system/ollama")
def get_ollama_runtime_status(current_user: User = Depends(get_current_user)):
    """Inspects the local Ollama LLM runtime and configured Qwen model."""
    from src.intelligence.event_extractor import check_ollama_status
    return check_ollama_status()


@router.post("/cases/{case_id}/events/extract", response_model=List[EventCandidateResponse])
def extract_case_events(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Extracts structured event candidates across all case evidence using local Qwen.
    Strictly preserves modality, tense (plans != completed events), and source citations.
    """
    evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    if not evidence_items:
        return []

    from src.intelligence.event_extractor import extract_events_with_qwen, EventCandidate
    from src.intelligence.timeline_builder import build_timeline_from_events
    from src.intelligence.evidence_reasoner import analyze_cross_evidence_relationships

    # Retrieve existing entity matches for actor context
    entity_records = db.query(EntityMatchRecord).filter(EntityMatchRecord.case_id == case_id).all()
    entities_context = [
        {"text": rec.canonical_name, "label": rec.entity_type}
        for rec in entity_records
    ]

    all_event_candidates: List[EventCandidate] = []

    for ev in evidence_items:
        if not ev.extracted_text or not ev.extracted_text.strip():
            file_path = Path(ev.stored_path)
            if file_path.exists():
                ext_res = run_pipeline_extraction(str(file_path), ev.file_type)
                ev.extracted_text = ext_res.get("text")
                ev.extraction_confidence = ext_res.get("confidence")
                db.flush()

        if ev.extracted_text and ev.extracted_text.strip():
            cands = extract_events_with_qwen(
                text=ev.extracted_text,
                case_id=case_id,
                evidence_id=ev.id,
                filename=ev.original_filename,
                entities=entities_context,
            )
            all_event_candidates.extend(cands)

    # Save to database: clear previous event extractions for this case to avoid stale data
    db.query(EventRecord).filter(EventRecord.case_id == case_id).delete()
    saved_records: List[EventRecord] = []
    seen_keys = set()
    for cand in all_event_candidates:
        key = (cand.title, cand.action, cand.original_time_expression)
        if key not in seen_keys:
            rec = EventRecord(
                id=cand.event_id,
                case_id=case_id,
                event_type=cand.event_type,
                title=cand.title,
                description=cand.description,
                actors_json=json.dumps(cand.actors),
                action=cand.action,
                location=cand.location,
                original_time_expression=cand.original_time_expression,
                normalized_start_time=cand.normalized_start_time,
                temporal_precision=cand.temporal_precision,
                evidence_ids_json=json.dumps(cand.evidence_ids),
                source_segment_ids_json=json.dumps(cand.source_segment_ids),
                supporting_text_spans_json=json.dumps(cand.supporting_text_spans),
                modality=cand.modality,
                explicit_or_inferred=cand.explicit_or_inferred,
                uncertainty_flags_json=json.dumps(cand.uncertainty_flags),
                validation_status=cand.validation_status,
                review_status=cand.review_status,
            )
            db.add(rec)
            saved_records.append(rec)
            seen_keys.add(key)

    # Build timeline & cross-evidence contradictions
    timeline = build_timeline_from_events(all_event_candidates, case_id=case_id)
    reasoning = analyze_cross_evidence_relationships(all_event_candidates, timeline)

    # Save detected contradictions
    db.query(EventContradictionRecord).filter(EventContradictionRecord.case_id == case_id).delete()
    for contra in reasoning.contradictions:
        c_rec = EventContradictionRecord(
            id=contra.contradiction_id,
            case_id=case_id,
            contradiction_type=contra.contradiction_type,
            description=contra.description,
            event_ids_json=json.dumps(contra.event_ids),
            evidence_ids_json=json.dumps(contra.evidence_ids),
            statement_a=contra.statement_a,
            statement_b=contra.statement_b,
            source_a=contra.source_a,
            source_b=contra.source_b,
            unresolved_question=contra.unresolved_question,
            resolution_status=contra.resolution_status,
        )
        db.add(c_rec)

    # Audit log
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        case_id=case_id,
        action="EVENTS_EXTRACTED_QWEN",
        details=json.dumps({
            "total_events_extracted": len(all_event_candidates),
            "contradictions_detected": len(reasoning.contradictions),
        }),
    )
    db.add(audit_entry)
    db.commit()

    # Query all events for response
    final_events = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
    result = []
    for r in final_events:
        result.append(
            EventCandidateResponse(
                id=r.id,
                case_id=r.case_id,
                event_type=r.event_type,
                title=r.title,
                description=r.description,
                actors=json.loads(r.actors_json) if r.actors_json else [],
                action=r.action,
                location=r.location,
                original_time_expression=r.original_time_expression,
                normalized_start_time=r.normalized_start_time,
                temporal_precision=r.temporal_precision,
                evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
                source_segment_ids=json.loads(r.source_segment_ids_json) if r.source_segment_ids_json else [],
                supporting_text_spans=json.loads(r.supporting_text_spans_json) if r.supporting_text_spans_json else [],
                modality=r.modality,
                explicit_or_inferred=r.explicit_or_inferred,
                uncertainty_flags=json.loads(r.uncertainty_flags_json) if r.uncertainty_flags_json else [],
                validation_status=r.validation_status,
                review_status=r.review_status,
                created_at=r.created_at,
            )
        )
    return result


@router.get("/cases/{case_id}/events", response_model=List[EventCandidateResponse])
def get_case_events(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns stored event candidates for a case."""
    records = db.query(EventRecord).filter(EventRecord.case_id == case_id).order_by(EventRecord.created_at.desc()).all()
    result = []
    for r in records:
        result.append(
            EventCandidateResponse(
                id=r.id,
                case_id=r.case_id,
                event_type=r.event_type,
                title=r.title,
                description=r.description,
                actors=json.loads(r.actors_json) if r.actors_json else [],
                action=r.action,
                location=r.location,
                original_time_expression=r.original_time_expression,
                normalized_start_time=r.normalized_start_time,
                temporal_precision=r.temporal_precision,
                evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
                source_segment_ids=json.loads(r.source_segment_ids_json) if r.source_segment_ids_json else [],
                supporting_text_spans=json.loads(r.supporting_text_spans_json) if r.supporting_text_spans_json else [],
                modality=r.modality,
                explicit_or_inferred=r.explicit_or_inferred,
                uncertainty_flags=json.loads(r.uncertainty_flags_json) if r.uncertainty_flags_json else [],
                validation_status=r.validation_status,
                review_status=r.review_status,
                created_at=r.created_at,
            )
        )
    return result


@router.get("/cases/{case_id}/timeline", response_model=TimelineResponse)
def get_case_timeline(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Computes a chronological timeline from event candidates, separates unscheduled events,
    annotates corroborations/contradictions, and applies user clarifications.
    """
    from src.intelligence.event_extractor import EventCandidate
    from src.intelligence.timeline_builder import build_timeline_from_events
    from src.intelligence.evidence_reasoner import analyze_cross_evidence_relationships
    from src.intelligence.clarification_engine import apply_clarifications_to_timeline, UserAnswer

    records = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
    events: List[EventCandidate] = []
    for r in records:
        events.append(
            EventCandidate(
                event_id=r.id,
                case_id=r.case_id,
                event_type=r.event_type,
                title=r.title,
                description=r.description,
                actors=json.loads(r.actors_json) if r.actors_json else [],
                action=r.action,
                location=r.location,
                original_time_expression=r.original_time_expression,
                normalized_start_time=r.normalized_start_time,
                temporal_precision=r.temporal_precision,
                evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
                source_segment_ids=json.loads(r.source_segment_ids_json) if r.source_segment_ids_json else [],
                supporting_text_spans=json.loads(r.supporting_text_spans_json) if r.supporting_text_spans_json else [],
                modality=r.modality,
                explicit_or_inferred=r.explicit_or_inferred,
                uncertainty_flags=json.loads(r.uncertainty_flags_json) if r.uncertainty_flags_json else [],
                validation_status=r.validation_status,
                review_status=r.review_status,
            )
        )

    timeline = build_timeline_from_events(events, case_id=case_id)
    analyze_cross_evidence_relationships(events, timeline)

    # Apply existing user answers
    answers_records = db.query(UserAnswerRecord).filter(UserAnswerRecord.case_id == case_id).all()
    user_answers = [
        UserAnswer(
            answer_id=a.id,
            question_id=a.question_id,
            case_id=a.case_id,
            event_id=a.event_id,
            selected_option=a.selected_option,
            free_text_clarification=a.free_text_clarification,
            user_surety=a.user_surety,
            surety_score=a.surety_score,
            knowledge_basis=a.knowledge_basis,
            submitted_at=a.submitted_at,
        )
        for a in answers_records
    ]
    apply_clarifications_to_timeline(timeline, user_answers, {})

    def to_entry_resp(e) -> TimelineEntryResponse:
        return TimelineEntryResponse(
            entry_id=e.entry_id,
            event_id=e.event_id,
            case_id=e.case_id,
            title=e.title,
            description=e.description,
            event_type=e.event_type,
            actors=e.actors,
            action=e.action,
            location=e.location,
            original_time_expression=e.original_time_expression,
            timestamp=e.timestamp,
            temporal_precision=e.temporal_precision,
            is_unscheduled=e.is_unscheduled,
            timeline_status=e.timeline_status,
            evidence_ids=e.evidence_ids,
            supporting_text_spans=e.supporting_text_spans,
            contradictions=e.contradictions,
            modality=e.modality,
        )

    return TimelineResponse(
        case_id=case_id,
        scheduled_events=[to_entry_resp(e) for e in timeline.scheduled_events],
        unscheduled_events=[to_entry_resp(e) for e in timeline.unscheduled_events],
        total_events_count=timeline.total_events_count,
        corroborated_count=timeline.corroborated_count,
        conflicting_count=timeline.conflicting_count,
        reconstructed_at=timeline.reconstructed_at,
    )


@router.get("/cases/{case_id}/contradictions", response_model=List[ContradictionResponse])
def get_case_contradictions(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns detected contradictions across evidence files."""
    records = db.query(EventContradictionRecord).filter(EventContradictionRecord.case_id == case_id).all()
    result = []
    for r in records:
        result.append(
            ContradictionResponse(
                id=r.id,
                case_id=r.case_id,
                contradiction_type=r.contradiction_type,
                description=r.description,
                event_ids=json.loads(r.event_ids_json) if r.event_ids_json else [],
                evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
                statement_a=r.statement_a,
                statement_b=r.statement_b,
                source_a=r.source_a,
                source_b=r.source_b,
                unresolved_question=r.unresolved_question,
                resolution_status=r.resolution_status,
                created_at=r.created_at,
            )
        )
    return result


@router.post("/cases/{case_id}/quiz/generate", response_model=List[ClarificationQuestionResponse])
def generate_case_quiz(case_id: str, db: Session = Depends(get_db)):
    """
    Generates targeted, non-leading clarification questions from real case ambiguities and contradictions.
    """
    from src.intelligence.event_extractor import EventCandidate
    from src.intelligence.timeline_builder import build_timeline_from_events
    from src.intelligence.evidence_reasoner import ContradictionRecord
    from src.intelligence.clarification_engine import generate_clarification_quiz

    event_records = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
    events = [
        EventCandidate(
            event_id=r.id,
            case_id=r.case_id,
            event_type=r.event_type,
            title=r.title,
            description=r.description,
            actors=json.loads(r.actors_json) if r.actors_json else [],
            action=r.action,
            original_time_expression=r.original_time_expression,
            normalized_start_time=r.normalized_start_time,
            temporal_precision=r.temporal_precision,
            evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
            modality=r.modality,
        )
        for r in event_records
    ]
    timeline = build_timeline_from_events(events, case_id=case_id)

    contra_records = db.query(EventContradictionRecord).filter(EventContradictionRecord.case_id == case_id).all()
    contradictions = [
        ContradictionRecord(
            contradiction_id=c.id,
            case_id=c.case_id,
            contradiction_type=c.contradiction_type,
            description=c.description,
            event_ids=json.loads(c.event_ids_json) if c.event_ids_json else [],
            evidence_ids=json.loads(c.evidence_ids_json) if c.evidence_ids_json else [],
            statement_a=c.statement_a,
            statement_b=c.statement_b,
            source_a=c.source_a,
            source_b=c.source_b,
            unresolved_question=c.unresolved_question,
        )
        for c in contra_records
    ]

    evidence_records = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    questions = generate_clarification_quiz(
        case_id=case_id,
        contradictions=contradictions,
        timeline=timeline,
        evidence_files=evidence_records,
        events=events,
    )

    # Save to database
    db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).delete()
    for q in questions:
        q_rec = ClarificationQuestionRecord(
            id=q.question_id,
            case_id=case_id,
            event_id=q.event_id,
            contradiction_id=q.contradiction_id,
            question_type=q.question_type,
            activity_name=q.activity_name,
            prompt=q.prompt,
            why_it_matters=q.why_it_matters,
            context_excerpt=q.context_excerpt,
            options_json=json.dumps(q.options),
            status=q.status,
        )
        db.add(q_rec)

    db.commit()

    saved_questions = db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).all()
    return [
        ClarificationQuestionResponse(
            id=sq.id,
            case_id=sq.case_id,
            event_id=sq.event_id,
            contradiction_id=sq.contradiction_id,
            question_type=sq.question_type,
            activity_name=getattr(sq, "activity_name", "") or "",
            prompt=sq.prompt,
            why_it_matters=getattr(sq, "why_it_matters", "") or "",
            context_excerpt=sq.context_excerpt,
            options=json.loads(sq.options_json) if sq.options_json else [],
            status=sq.status,
            created_at=sq.created_at,
        )
        for sq in saved_questions
    ]


@router.get("/cases/{case_id}/quiz", response_model=List[ClarificationQuestionResponse])
def get_case_quiz(case_id: str, db: Session = Depends(get_db)):
    """Returns stored clarification questions for a case."""
    questions = db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).all()
    return [
        ClarificationQuestionResponse(
            id=q.id,
            case_id=q.case_id,
            event_id=q.event_id,
            contradiction_id=q.contradiction_id,
            question_type=q.question_type,
            activity_name=getattr(q, "activity_name", "") or "",
            prompt=q.prompt,
            why_it_matters=getattr(q, "why_it_matters", "") or "",
            context_excerpt=q.context_excerpt,
            options=json.loads(q.options_json) if q.options_json else [],
            status=q.status,
            created_at=q.created_at,
        )
        for q in questions
    ]


@router.get("/cases/{case_id}/understanding", response_model=PreliminaryCaseUnderstandingResponse)
def get_case_understanding(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns preliminary case understanding ('What we understand so far'):
    key parties, established facts, proposed/planned actions, claims/allegations, and discrepancies.
    """
    from src.intelligence.event_extractor import EventCandidate
    from src.intelligence.evidence_reasoner import ContradictionRecord
    from src.intelligence.clarification_engine import generate_preliminary_case_understanding

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found.")

    evidence_records = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    event_records = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
    contra_records = db.query(EventContradictionRecord).filter(EventContradictionRecord.case_id == case_id).all()
    entity_records = db.query(EntityMatchRecord).filter(EntityMatchRecord.case_id == case_id).all()

    # If there are no evidence files or extracted events, return an empty pending-state response
    if not evidence_records and not event_records:
        return PreliminaryCaseUnderstandingResponse(
            case_id=case_id,
            narrative_summary="No evidence files or extracted events have been processed for this case yet.",
            key_parties=[],
            established_facts=[],
            proposed_or_planned=[],
            claims_and_allegations=[],
            unclear_or_disputed=[],
            evidence_sources=[],
        )

    def _safe_json_list(val: Any) -> list:
        if not val:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            val_s = val.strip()
            if val_s.startswith("[") and val_s.endswith("]"):
                try:
                    parsed = json.loads(val_s)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
        return []

    events = [
        EventCandidate(
            event_id=r.id,
            case_id=r.case_id,
            event_type=r.event_type,
            title=r.title,
            description=r.description,
            actors=_safe_json_list(r.actors_json),
            action=r.action,
            original_time_expression=r.original_time_expression,
            evidence_ids=_safe_json_list(r.evidence_ids_json),
            modality=r.modality,
            activity_name=getattr(r, "activity_name", "") or r.title,
            event_status=getattr(r, "event_status", "observed") or "observed",
            timestamp_type=getattr(r, "timestamp_type", "unknown") or "unknown",
            referenced_event_time=getattr(r, "referenced_event_time", None),
            is_communication=getattr(r, "is_communication", False) or False,
        )
        for r in event_records
    ]

    contradictions = [
        ContradictionRecord(
            contradiction_id=c.id,
            case_id=c.case_id,
            contradiction_type=c.contradiction_type,
            description=c.description,
            event_ids=_safe_json_list(c.event_ids_json),
            evidence_ids=_safe_json_list(c.evidence_ids_json),
            statement_a=c.statement_a,
            statement_b=c.statement_b,
            source_a=c.source_a,
            source_b=c.source_b,
            unresolved_question=c.unresolved_question,
            resolution_status=getattr(c, "resolution_status", "unresolved") or "unresolved",
        )
        for c in contra_records
    ]

    try:
        understanding = generate_preliminary_case_understanding(
            case_id=case_id,
            evidence_files=evidence_records,
            events=events,
            contradictions=contradictions,
            entities=entity_records,
        )
        return PreliminaryCaseUnderstandingResponse(
            case_id=understanding.case_id,
            narrative_summary=understanding.narrative_summary or "",
            key_parties=understanding.key_parties or [],
            established_facts=understanding.established_facts or [],
            proposed_or_planned=understanding.proposed_or_planned or [],
            claims_and_allegations=understanding.claims_and_allegations or [],
            unclear_or_disputed=understanding.unclear_or_disputed or [],
            evidence_sources=understanding.evidence_sources or [],
        )
    except Exception as exc:
        logger.error(f"Error generating case understanding for case {case_id}: {exc}", exc_info=True)
        return PreliminaryCaseUnderstandingResponse(
            case_id=case_id,
            narrative_summary="Preliminary case understanding is pending or being processed.",
            key_parties=[],
            established_facts=[],
            proposed_or_planned=[],
            claims_and_allegations=[],
            unclear_or_disputed=[],
            evidence_sources=[],
        )


@router.post("/cases/{case_id}/analysis/sync-mvp", response_model=MVPCaseAnalysisResponse)
def analyze_case_endpoint(case_id: str, db: Session = Depends(get_db)):
    """
    Executes simplified reliable MVP case analysis:
    - 150-250 word preliminary narrative
    - 5 to 10 evidence-backed facts with exact citations
    - 3 to 5 contextual unresolved questions
    - Timeline availability status
    """
    from src.intelligence.case_analyzer import analyze_case_mvp

    evidence_records = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    if not evidence_records:
        raise HTTPException(status_code=404, detail="No evidence files found for this case.")

    # Check existing timeline counts if available
    event_records = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
    scheduled_count = sum(1 for e in event_records if e.normalized_start_time is not None)
    unscheduled_count = len(event_records) - scheduled_count

    analysis = analyze_case_mvp(
        case_id=case_id,
        evidence_items=evidence_records,
        timeline_scheduled_count=scheduled_count,
        timeline_unscheduled_count=unscheduled_count,
    )

    # Sync unresolved questions to ClarificationQuestionRecord
    db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).delete()
    for q in analysis.unresolved_questions:
        q_rec = ClarificationQuestionRecord(
            id=q.question_id,
            case_id=case_id,
            question_type="case_clarification",
            activity_name=q.topic,
            prompt=q.question,
            why_it_matters=q.why_it_matters,
            context_excerpt=q.context_quote or (q.source_references[0] if q.source_references else "Case Evidence"),
            options_json=json.dumps(q.options),
            status=q.status,
        )
        db.add(q_rec)

    # Save to MVPAnalysisRecord
    db.query(MVPAnalysisRecord).filter(MVPAnalysisRecord.case_id == case_id).delete()
    mvp_rec = MVPAnalysisRecord(
        id=str(uuid.uuid4()),
        case_id=case_id,
        analysis_json=json.dumps(analysis.model_dump(), default=str),
    )
    db.add(mvp_rec)
    db.commit()

    return MVPCaseAnalysisResponse(
        id=mvp_rec.id,
        case_id=analysis.case_id,
        case_title=analysis.case_title,
        case_domain=analysis.case_domain,
        brief_summary=analysis.brief_summary,
        brief_summary_word_count=analysis.brief_summary_word_count,
        preliminary_narrative=analysis.preliminary_narrative,
        narrative_word_count=analysis.narrative_word_count,
        evidence_backed_facts=[f.model_dump() for f in analysis.evidence_backed_facts],
        unresolved_questions=[q.model_dump() for q in analysis.unresolved_questions],
        relevant_participants=analysis.relevant_participants,
        visual_findings=analysis.visual_findings,
        significant_communications=analysis.significant_communications,
        attributed_claims=analysis.attributed_claims,
        vision_enabled=analysis.vision_enabled,
        vision_status_summary=analysis.vision_status_summary,
        timeline_status=analysis.timeline_status,
        scheduled_events_count=analysis.scheduled_events_count,
        unscheduled_events_count=analysis.unscheduled_events_count,
        inference_source=analysis.inference_source,
        generated_at=analysis.generated_at,
    )


@router.get("/cases/{case_id}/analysis", response_model=MVPCaseAnalysisResponse)
def get_case_analysis_endpoint(case_id: str, db: Session = Depends(get_db)):
    """Returns stored MVP case analysis or generates one on-demand."""
    from backend.models import AnalysisJobRecord
    active_job = (
        db.query(AnalysisJobRecord)
        .filter(AnalysisJobRecord.case_id == case_id)
        .order_by(AnalysisJobRecord.created_at.desc())
        .first()
    )
    if active_job and active_job.status == "NO_ELIGIBLE_EVIDENCE":
        raise HTTPException(
            status_code=404,
            detail="No case analysis available: all evidence items were quarantined under the active evidence policy."
        )

    mvp_rec = db.query(MVPAnalysisRecord).filter(MVPAnalysisRecord.case_id == case_id).order_by(MVPAnalysisRecord.created_at.desc()).first()
    if not mvp_rec:
        return analyze_case_endpoint(case_id, db)

    data = json.loads(mvp_rec.analysis_json)
    return MVPCaseAnalysisResponse(
        id=mvp_rec.id,
        case_id=data.get("case_id", case_id),
        case_title=data.get("case_title", "Case Analysis"),
        case_domain=data.get("case_domain", "general_investigation"),
        brief_summary=data.get("brief_summary", ""),
        brief_summary_word_count=data.get("brief_summary_word_count", 0),
        preliminary_narrative=data.get("preliminary_narrative", ""),
        narrative_word_count=data.get("narrative_word_count", 0),
        evidence_backed_facts=data.get("evidence_backed_facts", []),
        unresolved_questions=data.get("unresolved_questions", []),
        relevant_participants=data.get("relevant_participants", []),
        visual_findings=data.get("visual_findings", []),
        significant_communications=data.get("significant_communications", []),
        attributed_claims=data.get("attributed_claims", []),
        vision_enabled=data.get("vision_enabled", True),
        vision_status_summary=data.get("vision_status_summary", "not_applicable"),
        authenticity_assessments=data.get("authenticity_assessments", []),
        authenticity_status_summary=data.get("authenticity_status_summary", "not_applicable"),
        timeline_status=data.get("timeline_status", "available"),
        scheduled_events_count=data.get("scheduled_events_count", 0),
        unscheduled_events_count=data.get("unscheduled_events_count", 0),
        inference_source=data.get("inference_source", "grounded_semantic_extractor"),
        generated_at=datetime.fromisoformat(data["generated_at"]) if "generated_at" in data else datetime.utcnow(),
    )


@router.post("/cases/{case_id}/quiz/answers", response_model=UserAnswerResponse)
def submit_quiz_answer(case_id: str, payload: SubmitAnswerPayload, db: Session = Depends(get_db)):
    """
    Submits user clarification answer with self-reported surety and knowledge basis.
    Preserves audit history and does not overwrite original evidence.
    """
    from src.intelligence.clarification_engine import SURETY_MAPPING

    q_rec = db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.id == payload.question_id).first()
    if not q_rec:
        raise HTTPException(status_code=404, detail="Question not found")

    surety_val = SURETY_MAPPING.get(payload.user_surety, 2)

    ans_rec = UserAnswerRecord(
        id=str(uuid.uuid4()),
        question_id=payload.question_id,
        case_id=case_id,
        event_id=q_rec.event_id,
        selected_option=payload.selected_option,
        free_text_clarification=payload.free_text_clarification,
        user_surety=payload.user_surety,
        surety_score=surety_val,
        knowledge_basis=payload.knowledge_basis,
    )
    db.add(ans_rec)

    # Mark question as answered
    q_rec.status = "answered"

    # Audit log
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        case_id=case_id,
        action="QUIZ_ANSWER_SUBMITTED",
        details=json.dumps({
            "question_id": payload.question_id,
            "answer": payload.selected_option,
            "user_surety": payload.user_surety,
            "knowledge_basis": payload.knowledge_basis,
        }),
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(ans_rec)

    return UserAnswerResponse(
        id=ans_rec.id,
        question_id=ans_rec.question_id,
        case_id=ans_rec.case_id,
        event_id=ans_rec.event_id,
        selected_option=ans_rec.selected_option,
        free_text_clarification=ans_rec.free_text_clarification,
        user_surety=ans_rec.user_surety,
        surety_score=ans_rec.surety_score,
        knowledge_basis=ans_rec.knowledge_basis,
        submitted_at=ans_rec.submitted_at,
    )


@router.post("/cases/{case_id}/reconstruct", response_model=TimelineResponse)
def trigger_iterative_reconstruction(case_id: str, db: Session = Depends(get_db)):
    """
    Iterative reconstruction: re-computes timeline incorporating witness clarifications.
    """
    return get_case_timeline(case_id=case_id, db=db)


@router.post("/cases/{case_id}/report/generate", response_model=ReportResponse)
def generate_case_report(case_id: str, db: Session = Depends(get_db)):
    """
    Synthesizes case evidence, timeline, contradictions, and user clarifications
    into a comprehensive forensic incident reconstruction report.
    """
    from src.intelligence.event_extractor import EventCandidate
    from src.intelligence.timeline_builder import build_timeline_from_events
    from src.intelligence.evidence_reasoner import ContradictionRecord
    from src.intelligence.clarification_engine import UserAnswer, ClarificationQuestion
    from src.reporting.report_generator import generate_forensic_incident_report, render_incident_report_html

    # Fetch evidence files
    evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    ev_list = [
        {
            "id": ev.id,
            "original_filename": ev.original_filename,
            "file_type": ev.file_type,
            "sha256": ev.sha256,
            "size_bytes": ev.size_bytes,
            "extraction_confidence": ev.extraction_confidence,
            "extracted_text": ev.extracted_text,
            "extraction_metadata": ev.extraction_metadata,
        }
        for ev in evidence_items
    ]

    # Fetch events & timeline
    event_records = db.query(EventRecord).filter(EventRecord.case_id == case_id).all()
    events = [
        EventCandidate(
            event_id=r.id,
            case_id=r.case_id,
            event_type=r.event_type,
            title=r.title,
            description=r.description,
            actors=json.loads(r.actors_json) if r.actors_json else [],
            action=r.action,
            original_time_expression=r.original_time_expression,
            normalized_start_time=r.normalized_start_time,
            temporal_precision=r.temporal_precision,
            evidence_ids=json.loads(r.evidence_ids_json) if r.evidence_ids_json else [],
            modality=r.modality,
        )
        for r in event_records
    ]
    timeline = build_timeline_from_events(events, case_id=case_id)

    # Fetch contradictions
    contra_records = db.query(EventContradictionRecord).filter(EventContradictionRecord.case_id == case_id).all()
    contradictions = [
        ContradictionRecord(
            contradiction_id=c.id,
            case_id=c.case_id,
            contradiction_type=c.contradiction_type,
            description=c.description,
            event_ids=json.loads(c.event_ids_json) if c.event_ids_json else [],
            evidence_ids=json.loads(c.evidence_ids_json) if c.evidence_ids_json else [],
            statement_a=c.statement_a,
            statement_b=c.statement_b,
            source_a=c.source_a,
            source_b=c.source_b,
            unresolved_question=c.unresolved_question,
        )
        for c in contra_records
    ]

    # Fetch quiz & answers
    q_records = db.query(ClarificationQuestionRecord).filter(ClarificationQuestionRecord.case_id == case_id).all()
    questions = [
        ClarificationQuestion(
            question_id=q.id,
            case_id=q.case_id,
            event_id=q.event_id,
            question_type=q.question_type,
            prompt=q.prompt,
            context_excerpt=q.context_excerpt,
            options=json.loads(q.options_json) if q.options_json else [],
            status=q.status,
        )
        for q in q_records
    ]

    ans_records = db.query(UserAnswerRecord).filter(UserAnswerRecord.case_id == case_id).all()
    answers = [
        UserAnswer(
            answer_id=a.id,
            question_id=a.question_id,
            case_id=a.case_id,
            event_id=a.event_id,
            selected_option=a.selected_option,
            free_text_clarification=a.free_text_clarification,
            user_surety=a.user_surety,
            surety_score=a.surety_score,
            knowledge_basis=a.knowledge_basis,
            submitted_at=a.submitted_at,
        )
        for a in ans_records
    ]

    # Fetch key entities
    entity_records = db.query(EntityMatchRecord).filter(EntityMatchRecord.case_id == case_id).all()
    ents_by_type: Dict[str, List[str]] = {}
    for er in entity_records:
        ents_by_type.setdefault(er.entity_type, []).append(er.canonical_name)

    report_obj = generate_forensic_incident_report(
        case_id=case_id,
        evidence_files=ev_list,
        timeline=timeline,
        contradictions=contradictions,
        questions=questions,
        answers=answers,
        entities_by_type=ents_by_type,
    )
    html_preview = render_incident_report_html(report_obj)

    # Save to database
    report_record = ReconstructedReportRecord(
        id=str(uuid.uuid4()),
        case_id=case_id,
        report_json=json.dumps(report_obj.model_dump(), default=str),
        html_preview=html_preview,
    )
    db.add(report_record)

    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        case_id=case_id,
        action="INCIDENT_REPORT_GENERATED",
        details=json.dumps({
            "report_id": report_record.id,
            "scheduled_events": len(report_obj.chronological_timeline),
            "contradictions": len(report_obj.contradictions_and_discrepancies),
        }),
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(report_record)

    return ReportResponse(
        id=report_record.id,
        case_id=report_record.case_id,
        report_data=report_obj.model_dump(),
        html_preview=html_preview,
        created_at=report_record.created_at,
    )


@router.get("/cases/{case_id}/report", response_model=ReportResponse)
def get_case_report(case_id: str, db: Session = Depends(get_db)):
    """Returns the latest reconstructed forensic incident report for a case."""
    from backend.models import AnalysisJobRecord
    active_job = (
        db.query(AnalysisJobRecord)
        .filter(AnalysisJobRecord.case_id == case_id)
        .order_by(AnalysisJobRecord.created_at.desc())
        .first()
    )
    if active_job and active_job.status == "NO_ELIGIBLE_EVIDENCE":
        raise HTTPException(
            status_code=404,
            detail="No report available: all evidence items were quarantined under the active evidence policy."
        )

    report_rec = (
        db.query(ReconstructedReportRecord)
        .filter(ReconstructedReportRecord.case_id == case_id)
        .order_by(ReconstructedReportRecord.created_at.desc())
        .first()
    )
    if not report_rec:
        raise HTTPException(status_code=404, detail="Report not yet generated for this case.")

    return ReportResponse(
        id=report_rec.id,
        case_id=report_rec.case_id,
        report_data=json.loads(report_rec.report_json),
        html_preview=report_rec.html_preview,
        created_at=report_rec.created_at,
    )


@router.get("/cases/{case_id}/report/html", response_class=HTMLResponse)
def get_case_report_html(case_id: str, db: Session = Depends(get_db)):
    """Returns the printable HTML incident report view for browser viewing or saving as PDF."""
    from backend.models import AnalysisJobRecord
    active_job = (
        db.query(AnalysisJobRecord)
        .filter(AnalysisJobRecord.case_id == case_id)
        .order_by(AnalysisJobRecord.created_at.desc())
        .first()
    )
    if active_job and active_job.status == "NO_ELIGIBLE_EVIDENCE":
        raise HTTPException(
            status_code=404,
            detail="No report available: all evidence items were quarantined under the active evidence policy."
        )

    report_rec = (
        db.query(ReconstructedReportRecord)
        .filter(ReconstructedReportRecord.case_id == case_id)
        .order_by(ReconstructedReportRecord.created_at.desc())
        .first()
    )
    if not report_rec:
        raise HTTPException(status_code=404, detail="Report not yet generated for this case.")

    return HTMLResponse(content=report_rec.html_preview, status_code=200)


# =========================================================================
# ONE-CLICK END-TO-END ANALYSIS JOB CONTROL ENDPOINTS
# =========================================================================

class StartAnalysisPayload(BaseModel):
    policy_mode: Optional[str] = "DEVELOPMENT"
    force_reanalysis: Optional[bool] = False


class QuarantineEvidencePayload(BaseModel):
    review_status: str
    reason: Optional[str] = None


class QuizSubmissionPayload(BaseModel):
    answers: Optional[List[SubmitAnswerPayload]] = None
    question_id: Optional[str] = None
    selected_option: Optional[str] = None
    free_text_clarification: Optional[str] = None
    user_surety: str = "Fairly sure"
    knowledge_basis: str = "Not specified"


@router.post("/cases/{case_id}/evidence/{evidence_id}/quarantine", response_model=EvidenceResponse)
def update_evidence_quarantine_endpoint(
    case_id: str,
    evidence_id: str,
    payload: QuarantineEvidencePayload,
    db: Session = Depends(get_db)
):
    """
    Manually update evidence review status (quarantine override or restore).
    Records append-only forensic audit trail.
    """
    valid_statuses = {
        "EXCLUDED_BY_INVESTIGATOR",
        "RESTORED_BY_INVESTIGATOR",
        "INCLUDED",
        "FLAGGED_FOR_REVIEW",
        "EXCLUDED_BY_POLICY",
    }
    if payload.review_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid review_status '{payload.review_status}'. Allowed: {sorted(list(valid_statuses))}",
        )

    ev = db.query(Evidence).filter(Evidence.id == evidence_id, Evidence.case_id == case_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found for this case.")

    ev.review_status = payload.review_status
    if payload.reason:
        ev.quarantine_reason = payload.reason
    elif payload.review_status == "RESTORED_BY_INVESTIGATOR":
        ev.quarantine_reason = "Manually restored by investigator override."
    elif payload.review_status == "EXCLUDED_BY_INVESTIGATOR":
        ev.quarantine_reason = "Manually excluded by investigator override."

    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        case_id=case_id,
        evidence_id=evidence_id,
        action="EVIDENCE_QUARANTINE_UPDATED",
        details=json.dumps({
            "review_status": payload.review_status,
            "reason": ev.quarantine_reason,
        }),
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/cases/{case_id}/analyze")
def start_case_analysis_endpoint(
    case_id: str,
    payload: Optional[StartAnalysisPayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the one-click end-to-end investigative analysis pipeline.
    Creates a persistent job tracking 18 discrete stages and starts execution.
    Supports configurable policy_mode: 'DEVELOPMENT' (default) or 'STRICT_REVIEW'.
    """
    from backend.services.analysis_orchestrator import (
        create_analysis_job, start_orchestrated_analysis, get_job_with_stages
    )
    case = db.query(Case).filter(Case.id == case_id).first()
    check_case_access(case, current_user)

    evidence_count = db.query(Evidence).filter(Evidence.case_id == case_id).count()
    if evidence_count == 0:
        raise HTTPException(status_code=400, detail="Cannot analyze case with zero evidence items.")

    policy_mode = (payload.policy_mode if payload and payload.policy_mode else "DEVELOPMENT").upper()
    force_reanalysis = payload.force_reanalysis if payload and payload.force_reanalysis is not None else False
    job = create_analysis_job(case_id, policy_mode=policy_mode, force_reanalysis=force_reanalysis)
    if job.status in ["PENDING"]:
        start_orchestrated_analysis(job.id)

    job_data = get_job_with_stages(job.id)
    return job_data


@router.get("/cases/{case_id}/analysis/active-job")
def get_active_case_job_endpoint(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = db.query(Case).filter(Case.id == case_id).first()
    check_case_access(case, current_user)
    """
    Returns the active (or latest) job for a case to restore UI state across refreshes.
    Returns None if no job exists for the case.
    """
    from backend.services.analysis_orchestrator import get_active_job_for_case
    job_data = get_active_job_for_case(case_id)
    return job_data


@router.get("/analysis/jobs/{job_id}")
def get_analysis_job_endpoint(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the current execution state, progress percentage, and stage info of an analysis job.
    """
    from backend.services.analysis_orchestrator import get_job_with_stages
    job_data = get_job_with_stages(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    case = db.query(Case).filter(Case.id == job_data.get("case_id")).first()
    check_case_access(case, current_user)
    return job_data


@router.get("/analysis/jobs/{job_id}/stages")
def get_analysis_job_stages_endpoint(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns detailed progression status, timestamps, and duration for all 15 stages.
    """
    from backend.services.analysis_orchestrator import get_job_with_stages
    job_data = get_job_with_stages(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    case = db.query(Case).filter(Case.id == job_data.get("case_id")).first()
    check_case_access(case, current_user)
    return job_data.get("stages", [])


@router.get("/analysis/jobs/{job_id}/result")
def get_analysis_job_result_endpoint(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the analytical artifacts generated by the job (preliminary story or final report).
    """
    from backend.services.analysis_orchestrator import get_job_with_stages
    job_data = get_job_with_stages(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    case = db.query(Case).filter(Case.id == job_data.get("case_id")).first()
    check_case_access(case, current_user)
    return {
        "job_id": job_id,
        "case_id": job_data["case_id"],
        "status": job_data["status"],
        "artifacts": job_data.get("artifacts", {}),
    }


@router.post("/analysis/jobs/{job_id}/retry")
def retry_analysis_job_endpoint(job_id: str):
    """
    Resumes a failed job from the point of failure without restarting finished stages.
    """
    from backend.services.analysis_orchestrator import retry_failed_job
    try:
        updated_job = retry_failed_job(job_id)
        return updated_job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")


@router.get("/analysis/jobs/{job_id}/quiz", response_model=List[ClarificationQuestionResponse])
def get_analysis_job_quiz_endpoint(job_id: str, db: Session = Depends(get_db)):
    """
    Returns the clarification questions generated for the job's case.
    """
    from backend.services.analysis_orchestrator import get_job_with_stages
    job_data = get_job_with_stages(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Analysis job not found.")

    case_id = job_data["case_id"]
    q_records = (
        db.query(ClarificationQuestionRecord)
        .filter(ClarificationQuestionRecord.case_id == case_id)
        .order_by(ClarificationQuestionRecord.created_at.asc())
        .all()
    )

    questions: List[ClarificationQuestionResponse] = []
    for q in q_records:
        opts = json.loads(q.options_json) if q.options_json else []
        questions.append(
            ClarificationQuestionResponse(
                id=q.id,
                case_id=q.case_id,
                event_id=q.event_id,
                contradiction_id=q.contradiction_id,
                question_type=q.question_type,
                activity_name=q.activity_name or "",
                prompt=q.prompt,
                why_it_matters=q.why_it_matters or "",
                context_excerpt=q.context_excerpt or "",
                options=opts,
                status=q.status or "unanswered",
                created_at=q.created_at,
            )
        )
    return questions


@router.post("/analysis/jobs/{job_id}/quiz/submit")
def submit_analysis_job_quiz_endpoint(job_id: str, payload: QuizSubmissionPayload):
    """
    Accepts clarification answers for a job awaiting user testimony,
    persists the answers, and automatically resumes pipeline execution.
    """
    from backend.db import SessionLocal
    from backend.services.analysis_orchestrator import (
        get_job_with_stages, resume_analysis_after_quiz_submission
    )

    with SessionLocal() as db:
        job_rec = db.query(AnalysisJobRecord).filter(AnalysisJobRecord.id == job_id).first()
        if not job_rec:
            raise HTTPException(status_code=404, detail="Analysis job not found.")
        case_id = job_rec.case_id

        # Flatten answer list
        answer_items: List[SubmitAnswerPayload] = []
        if payload.answers:
            answer_items.extend(payload.answers)
        elif payload.question_id and payload.selected_option:
            answer_items.append(SubmitAnswerPayload(
                question_id=payload.question_id,
                selected_option=payload.selected_option,
                free_text_clarification=payload.free_text_clarification,
                user_surety=payload.user_surety,
                knowledge_basis=payload.knowledge_basis,
            ))

        if not answer_items:
            raise HTTPException(status_code=400, detail="No answers provided in submission.")

        surety_scores = {
            "Very sure": 100,
            "Fairly sure": 75,
            "Somewhat sure": 50,
            "Unsure": 25,
            "Do not remember": 0,
        }

        saved_count = 0
        for ans in answer_items:
            q_rec = db.query(ClarificationQuestionRecord).filter(
                ClarificationQuestionRecord.id == ans.question_id
            ).first()
            if q_rec:
                q_rec.status = "answered"

            score = surety_scores.get(ans.user_surety, 75)
            ans_rec = UserAnswerRecord(
                id=str(uuid.uuid4()),
                question_id=ans.question_id,
                case_id=case_id,
                event_id=q_rec.event_id if q_rec else None,
                selected_option=ans.selected_option,
                free_text_clarification=ans.free_text_clarification,
                user_surety=ans.user_surety,
                surety_score=score,
                knowledge_basis=ans.knowledge_basis or "Direct first-hand knowledge",
                submitted_at=datetime.utcnow(),
            )
            db.add(ans_rec)
            saved_count += 1

        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case_id,
            action="JOB_QUIZ_ANSWERS_SUBMITTED",
            details=json.dumps({"job_id": job_id, "answers_count": saved_count}),
        )
        db.add(audit_entry)
        db.commit()

    # Resume the analysis pipeline
    resume_analysis_after_quiz_submission(job_id)

    updated_job = get_job_with_stages(job_id)
    return {
        "status": "RESUMED",
        "job_id": job_id,
        "answers_recorded": saved_count,
        "job": updated_job,
    }




