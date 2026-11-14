"""GLiNER Entity Extraction module for Evidence AI.

Extracts persons, organizations, locations, dates, times, and forensic identifiers
using urchade/gliner_small-v2.1 with regex supplements.
"""

import os
import re
import threading
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Ensure local cache is used and offline mode enabled for speed & sandbox compatibility
os.environ.setdefault("HF_HOME", r"c:\project\models_cache\huggingface")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

DEFAULT_LABELS = [
    "person",
    "organization",
    "location",
    "date",
    "time",
    "identifier",
    "phone number",
    "email address",
    "financial account",
]

# Regex supplements for forensic precision
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
IP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DATE_REGEX = re.compile(r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b")


class ExtractedEntity(BaseModel):
    """An extracted named entity mention."""
    text: str
    label: str                     # person | organization | location | date | time | identifier
    confidence: float
    start_char: int
    end_char: int
    evidence_id: Optional[str] = None
    filename: Optional[str] = None
    source_segment_id: Optional[str] = None


class GLiNERModelManager:
    """Thread-safe singleton manager for lazy-loaded GLiNER model."""
    _instance = None
    _lock = threading.Lock()
    _model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from gliner import GLiNER
                    try:
                        # Fast offline load from local cache
                        self._model = GLiNER.from_pretrained("urchade/gliner_small-v2.1", local_files_only=True)
                    except Exception:
                        self._model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
        return self._model


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[Dict[str, Any]]:
    """Chunks long text into overlapping windows for model inference."""
    if len(text) <= max_chars:
        return [{"text": text, "offset": 0}]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + max_chars, text_len)
        # Try to break at a newline or space
        if end < text_len:
            space_idx = text.rfind(" ", start, end)
            if space_idx > start + (max_chars // 2):
                end = space_idx

        chunk_str = text[start:end]
        chunks.append({"text": chunk_str, "offset": start})
        if end >= text_len:
            break
        start = max(start + 1, end - overlap)

    return chunks


def extract_entities_from_text(
    text: str,
    evidence_id: Optional[str] = None,
    filename: Optional[str] = None,
    threshold: float = 0.35,
    custom_labels: Optional[List[str]] = None,
) -> List[ExtractedEntity]:
    """
    Extracts entities from text using GLiNER with regex augmentation.
    """
    if not text or not text.strip():
        return []

    labels = custom_labels or DEFAULT_LABELS
    model = GLiNERModelManager.get_instance().get_model()

    extracted: List[ExtractedEntity] = []
    seen_spans = set()

    chunks = chunk_text(text)
    for ch in chunks:
        chunk_str = ch["text"]
        offset = ch["offset"]

        try:
            preds = model.predict_entities(chunk_str, labels, threshold=threshold)
            for p in preds:
                p_text = p.get("text", "").strip()
                p_label = p.get("label", "").lower()
                p_score = float(p.get("score", 0.0))
                abs_start = offset + int(p.get("start", 0))
                abs_end = offset + int(p.get("end", 0))

                # Normalize label
                if p_label in ["phone number", "email address", "financial account"]:
                    normalized_label = "identifier"
                elif p_label in ["person", "organization", "location", "date", "time", "identifier"]:
                    normalized_label = p_label
                else:
                    normalized_label = "identifier"

                span_key = (p_text.lower(), normalized_label, abs_start, abs_end)
                if span_key not in seen_spans and len(p_text) >= 2:
                    seen_spans.add(span_key)
                    extracted.append(
                        ExtractedEntity(
                            text=p_text,
                            label=normalized_label,
                            confidence=round(p_score, 4),
                            start_char=abs_start,
                            end_char=abs_end,
                            evidence_id=evidence_id,
                            filename=filename,
                        )
                    )
        except Exception:
            pass

    # Regex supplements for emails
    for m in EMAIL_REGEX.finditer(text):
        m_text = m.group()
        span_key = (m_text.lower(), "identifier", m.start(), m.end())
        if span_key not in seen_spans:
            seen_spans.add(span_key)
            extracted.append(
                ExtractedEntity(
                    text=m_text,
                    label="identifier",
                    confidence=0.99,
                    start_char=m.start(),
                    end_char=m.end(),
                    evidence_id=evidence_id,
                    filename=filename,
                )
            )

    # Regex supplements for phone numbers
    for m in PHONE_REGEX.finditer(text):
        m_text = m.group()
        span_key = (m_text.lower(), "identifier", m.start(), m.end())
        if span_key not in seen_spans and len(m_text.strip()) >= 7:
            seen_spans.add(span_key)
            extracted.append(
                ExtractedEntity(
                    text=m_text,
                    label="identifier",
                    confidence=0.95,
                    start_char=m.start(),
                    end_char=m.end(),
                    evidence_id=evidence_id,
                    filename=filename,
                )
            )

    # Regex supplements for IP addresses
    for m in IP_REGEX.finditer(text):
        m_text = m.group()
        span_key = (m_text.lower(), "identifier", m.start(), m.end())
        if span_key not in seen_spans:
            seen_spans.add(span_key)
            extracted.append(
                ExtractedEntity(
                    text=m_text,
                    label="identifier",
                    confidence=0.98,
                    start_char=m.start(),
                    end_char=m.end(),
                    evidence_id=evidence_id,
                    filename=filename,
                )
            )

    # Sort by character position in document
    extracted.sort(key=lambda e: e.start_char)
    return extracted
