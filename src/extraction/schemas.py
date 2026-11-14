"""Data schemas for normalized forensic extraction records."""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceLocation(BaseModel):
    """Pinpoints the exact location in the original evidence source."""
    page_number: Optional[int] = None       # For PDFs / DOCX pages
    paragraph_index: Optional[int] = None   # For DOCX
    table_index: Optional[int] = None       # For DOCX / CSV
    row_index: Optional[int] = None         # For CSV / Tables
    line_number: Optional[int] = None       # For plain text / logs
    start_time: Optional[float] = None      # Audio timestamp start in seconds
    end_time: Optional[float] = None        # Audio timestamp end in seconds
    sender: Optional[str] = None            # Chat sender / Email sender
    timestamp: Optional[str] = None         # In-content timestamp if present
    bbox: Optional[List[List[int]]] = None  # OCR bounding box polygon


class EvidenceSegment(BaseModel):
    """An atomic text segment linked to its original source location."""
    segment_id: str
    text: str
    location: SourceLocation = Field(default_factory=SourceLocation)
    confidence: float = 1.0
    is_ocr: bool = False


class NormalizedExtractionRecord(BaseModel):
    """Unified normalized extraction schema across all evidence modalities."""
    evidence_id: Optional[str] = None
    filename: str
    sha256: str
    file_type: str                         # image | audio | pdf | docx | text | json | csv | eml
    mime_type: Optional[str] = None
    size_bytes: int = 0
    full_text: str
    overall_confidence: float = 1.0
    segments: List[EvidenceSegment] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)
