"""Unified Extraction Pipeline router for Evidence AI.

Handles images (PaddleOCR), audio (Faster-Whisper), PDFs (hybrid PyPDF/PaddleOCR),
DOCX (python-docx), and structured text/chat logs (JSON, CSV, EML, TXT).
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.extraction.schemas import NormalizedExtractionRecord, EvidenceSegment, SourceLocation


def compute_sha256(file_path: Union[str, Path]) -> str:
    """Computes SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def process_evidence(
    file_path: Union[str, Path],
    evidence_id: Optional[str] = None,
    filename: Optional[str] = None,
    file_category: Optional[str] = None,
    sha256_hash: Optional[str] = None,
) -> NormalizedExtractionRecord:
    """
    Main entry point for evidence extraction.
    Routes to the appropriate modality parser and returns a normalized record.
    """
    path_obj = Path(file_path).resolve()
    if not path_obj.is_file():
        raise FileNotFoundError(f"Evidence file not found: {path_obj}")

    fname = filename or path_obj.name
    sha256 = sha256_hash or compute_sha256(path_obj)
    size_bytes = path_obj.stat().st_size
    mime_type, _ = mimetypes.guess_type(fname)
    ext = path_obj.suffix.lower()

    # Determine internal file category if not supplied
    if not file_category:
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            file_category = "image"
        elif ext in {".mp3", ".wav", ".m4a", ".ogg"}:
            file_category = "audio"
        elif ext == ".pdf":
            file_category = "pdf"
        elif ext == ".docx":
            file_category = "docx"
        elif ext == ".eml":
            file_category = "eml"
        elif ext == ".json":
            file_category = "json"
        elif ext == ".csv":
            file_category = "csv"
        else:
            file_category = "text"

    try:
        if file_category == "image":
            from src.extraction.ocr import extract_text_from_image
            ocr_res = extract_text_from_image(str(path_obj))

            segments = []
            for idx, line in enumerate(ocr_res.get("lines", []), 1):
                segments.append(
                    EvidenceSegment(
                        segment_id=f"line-{idx}",
                        text=line.get("text", ""),
                        location=SourceLocation(line_number=idx, bbox=line.get("bbox")),
                        confidence=float(line.get("confidence", ocr_res.get("confidence", 0.0))),
                        is_ocr=True,
                    )
                )

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="image",
                mime_type=mime_type or "image/png",
                size_bytes=size_bytes,
                full_text=ocr_res.get("text", ""),
                overall_confidence=ocr_res.get("confidence", 0.0),
                segments=segments,
                metadata={
                    "engine": "PaddleOCR PP-OCRv6_small",
                    "lines_count": len(segments),
                },
                processing_time_ms=ocr_res.get("processing_time_ms", 0.0),
                success=True,
            )

        elif file_category == "audio":
            from src.extraction.transcription import transcribe_audio
            audio_res = transcribe_audio(str(path_obj))

            segments = []
            for seg in audio_res.get("segments", []):
                segments.append(
                    EvidenceSegment(
                        segment_id=f"seg-{seg.get('id', 0)}",
                        text=seg.get("text", ""),
                        location=SourceLocation(
                            start_time=seg.get("start"),
                            end_time=seg.get("end"),
                        ),
                        confidence=float(seg.get("confidence", 0.9)),
                        is_ocr=False,
                    )
                )

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="audio",
                mime_type=mime_type or "audio/wav",
                size_bytes=size_bytes,
                full_text=audio_res.get("text", ""),
                overall_confidence=audio_res.get("language_probability", 0.9),
                segments=segments,
                metadata={
                    "engine": "Faster-Whisper Small",
                    "language": audio_res.get("language"),
                    "duration": audio_res.get("duration"),
                },
                processing_time_ms=audio_res.get("processing_time_ms", 0.0),
                success=True,
            )

        elif ext == ".pdf":
            from src.extraction.pdf_extractor import extract_pdf
            pdf_res = extract_pdf(str(path_obj))

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="pdf",
                mime_type=mime_type or "application/pdf",
                size_bytes=size_bytes,
                full_text=pdf_res.get("text", ""),
                overall_confidence=pdf_res.get("confidence", 1.0),
                segments=[EvidenceSegment(**s) for s in pdf_res.get("segments", [])],
                metadata=pdf_res.get("metadata", {}),
                processing_time_ms=pdf_res.get("processing_time_ms", 0.0),
                success=True,
            )

        elif ext == ".docx":
            from src.extraction.docx_extractor import extract_docx
            docx_res = extract_docx(str(path_obj))

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="docx",
                mime_type=mime_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                size_bytes=size_bytes,
                full_text=docx_res.get("text", ""),
                overall_confidence=docx_res.get("confidence", 1.0),
                segments=[EvidenceSegment(**s) for s in docx_res.get("segments", [])],
                metadata=docx_res.get("metadata", {}),
                processing_time_ms=docx_res.get("processing_time_ms", 0.0),
                success=True,
            )

        elif ext == ".eml":
            from src.extraction.structured_chat_extractor import extract_eml
            eml_res = extract_eml(str(path_obj))

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="eml",
                mime_type=mime_type or "message/rfc822",
                size_bytes=size_bytes,
                full_text=eml_res.get("text", ""),
                overall_confidence=eml_res.get("confidence", 1.0),
                segments=[EvidenceSegment(**s) for s in eml_res.get("segments", [])],
                metadata=eml_res.get("metadata", {}),
                processing_time_ms=eml_res.get("processing_time_ms", 0.0),
                success=True,
            )

        elif ext == ".json":
            from src.extraction.structured_chat_extractor import extract_json_chat
            json_res = extract_json_chat(str(path_obj))

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="json",
                mime_type=mime_type or "application/json",
                size_bytes=size_bytes,
                full_text=json_res.get("text", ""),
                overall_confidence=json_res.get("confidence", 1.0),
                segments=[EvidenceSegment(**s) for s in json_res.get("segments", [])],
                metadata=json_res.get("metadata", {}),
                processing_time_ms=json_res.get("processing_time_ms", 0.0),
                success=True,
            )

        elif ext == ".csv":
            from src.extraction.structured_chat_extractor import extract_csv
            csv_res = extract_csv(str(path_obj))

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="csv",
                mime_type=mime_type or "text/csv",
                size_bytes=size_bytes,
                full_text=csv_res.get("text", ""),
                overall_confidence=csv_res.get("confidence", 1.0),
                segments=[EvidenceSegment(**s) for s in csv_res.get("segments", [])],
                metadata=csv_res.get("metadata", {}),
                processing_time_ms=csv_res.get("processing_time_ms", 0.0),
                success=True,
            )

        else:
            # Default to text / chat
            from src.extraction.structured_chat_extractor import extract_txt_chat
            txt_res = extract_txt_chat(str(path_obj))

            return NormalizedExtractionRecord(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                file_type="text",
                mime_type=mime_type or "text/plain",
                size_bytes=size_bytes,
                full_text=txt_res.get("text", ""),
                overall_confidence=txt_res.get("confidence", 1.0),
                segments=[EvidenceSegment(**s) for s in txt_res.get("segments", [])],
                metadata=txt_res.get("metadata", {}),
                processing_time_ms=txt_res.get("processing_time_ms", 0.0),
                success=True,
            )

    except Exception as exc:
        return NormalizedExtractionRecord(
            evidence_id=evidence_id,
            filename=fname,
            sha256=sha256,
            file_type=file_category or "unknown",
            mime_type=mime_type,
            size_bytes=size_bytes,
            full_text="",
            overall_confidence=0.0,
            segments=[],
            metadata={"error": str(exc)},
            processing_time_ms=0.0,
            success=False,
            error=str(exc),
        )
