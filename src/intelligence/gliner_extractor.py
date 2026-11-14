"""GLiNER Entity Extraction module for Evidence AI.

Extracts persons, organizations, locations, dates, times, and forensic identifiers
using urchade/gliner_small-v2.1 with regex supplements and strict validation filters.
"""

import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple
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

# Job titles and roles that must NOT be classified as organizations or standalone entities
JOB_TITLES = {
    "director", "managing director", "executive director", "associate director", "regional director",
    "manager", "general manager", "operations manager", "project manager",
    "chief executive officer", "ceo", "chief technology officer", "cto",
    "chief financial officer", "cfo", "chief operating officer", "coo",
    "president", "vice president", "vp", "senior vice president", "svp",
    "analyst", "senior analyst", "research analyst",
    "investigator", "lead investigator", "detective", "officer", "agent",
    "engineer", "software engineer", "senior software engineer", "developer",
    "consultant", "senior consultant", "supervisor", "administrator", "head of operations",
    "associate", "coordinator", "assistant", "auditor", "legal counsel", "attorney",
    "partner", "managing partner", "senior partner", "equity partner", "junior partner", "general partner", "limited partner",
    "specialist", "case officer", "founder", "co-founder", "chairman", "chairperson",
    "board member", "trustee", "principal"
}

# Generic words / email interface keywords that must NOT be classified as identifiers or organizations
GENERIC_NOISE_WORDS = {
    "inbox", "sent", "drafts", "trash", "archive", "junk", "spam",
    "subject", "re", "fwd", "fw", "official work email", "work email",
    "personal email", "email", "mail", "message", "messages", "to", "from",
    "cc", "bcc", "date", "time", "attachment", "attachments", "confidential",
    "reply", "forward", "urgent", "general", "notes", "file", "document",
    "dear", "regards", "sincerely", "thanks", "thank you", "hello", "hi",
    "status", "update", "notification", "alert", "report", "case",
    "portal", "web portal", "customer portal", "employee portal", "admin portal",
    "client portal", "user portal", "payment portal", "online portal",
    "website", "dashboard", "platform", "system", "app", "application", "server",
    "intranet", "extranet", "interface", "database", "feed", "log", "logs",
    "form", "page", "site", "online", "online banking", "login", "logout",
    "signin", "signout", "homepage", "tab", "window", "folder", "directory",
    "software", "portal access"
}


class ExtractedEntity(BaseModel):
    """An extracted named entity mention."""
    text: str
    label: str                     # person | organization | location | date | time | identifier
    confidence: float              # GLiNER classification confidence
    ocr_confidence: Optional[float] = None # Source OCR/ASR extraction confidence
    start_char: int
    end_char: int
    evidence_id: Optional[str] = None
    filename: Optional[str] = None
    source_segment_id: Optional[str] = None
    is_low_confidence: bool = False
    requires_source_verification: bool = False
    quality_flags: List[str] = Field(default_factory=list)


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


def is_valid_identifier(text: str) -> bool:
    """
    Validates whether a text span is a legitimate identifier (email, phone, IP, or code with digits/symbols).
    Rejects generic noise words ('inbox', 'official work email') and purely alphabetic prose phrases.
    """
    clean = text.strip()
    clean_lower = clean.lower()

    if len(clean) < 2:
        return False

    if clean_lower in GENERIC_NOISE_WORDS:
        return False

    is_email = bool(EMAIL_REGEX.search(clean))
    is_phone = bool(PHONE_REGEX.search(clean))
    is_ip = bool(IP_REGEX.search(clean))
    has_digits_or_symbols = bool(re.search(r"[\d#\-_@.:/\\]", clean))

    return bool(is_email or is_phone or is_ip or has_digits_or_symbols)


def is_noise_or_job_title(clean_lower: str, label: str) -> bool:
    """Checks if text is generic noise or a job title misclassified as an organization."""
    if clean_lower in GENERIC_NOISE_WORDS:
        return True

    if label == "organization":
        if clean_lower in JOB_TITLES:
            return True
        # Check title patterns (e.g. 'Managing Partner', 'Senior Director', 'General Counsel')
        title_suffixes = ("partner", "director", "manager", "officer", "president", "counsel", "consultant", "analyst", "engineer", "lead", "administrator")
        if any(clean_lower == s or clean_lower.endswith(" " + s) for s in title_suffixes):
            return True
        # Generic single nouns commonly hallucinated as organizations
        if clean_lower in {"portal", "website", "platform", "system", "dashboard", "interface", "application", "database", "server", "intranet", "portal access"}:
            return True

    return False


def evaluate_entity_quality(
    text: str,
    label: str,
    confidence: float,
    ocr_confidence: Optional[float] = None,
) -> Tuple[bool, bool, List[str]]:
    """
    Evaluates whether an entity is low confidence or requires source verification.
    Preserves questionable or garbled OCR detections instead of silently dropping them.
    Prioritizes forensic identifiers (such as KL-8842) for source-image verification.

    Returns:
        (is_low_confidence, requires_source_verification, quality_flags)
    """
    flags: List[str] = []
    is_low_conf = False
    req_verify = False

    # 1. Classification confidence check
    if confidence < 0.55:
        is_low_conf = True
        flags.append("low_classification_confidence")

    # 2. Source OCR confidence check
    if ocr_confidence is not None and ocr_confidence < 0.75:
        is_low_conf = True
        req_verify = True
        flags.append(f"low_ocr_confidence_{int(ocr_confidence * 100)}pct")

    # 3. Garbled / questionable OCR artifacts (repeated punctuation, corrupt symbols)
    has_repeated_punct = bool(re.search(r"[,._:;\-~^|\\\/]{2,}", text))
    has_strange_chars = bool(re.search(r"[~^|\\\[\]{}]", text))
    if has_repeated_punct or has_strange_chars:
        is_low_conf = True
        req_verify = True
        flags.append("garbled_ocr_artifacts")

    # 4. Critical forensic identifiers (e.g. vehicle plates like KL-8842, serial codes)
    if label == "identifier":
        is_plate_or_code = bool(re.search(r"^[A-Z]{2}[-\s]?\d{3,5}$", text.strip(), re.IGNORECASE))
        if is_plate_or_code or confidence < 0.85 or (ocr_confidence is not None and ocr_confidence < 0.90):
            req_verify = True
            flags.append("identifier_source_verification_priority")

    return is_low_conf, req_verify, flags


def validate_and_filter_entity(
    text: str,
    label: str,
    confidence: float,
    ocr_confidence: Optional[float] = None,
) -> Tuple[bool, str, bool, bool, List[str]]:
    """
    Validates entity category, filters false positives (job titles, noise words),
    and marks questionable/garbled detections for the low-confidence review category.

    Returns:
        (is_valid, normalized_label, is_low_confidence, requires_source_verification, quality_flags)
    """
    clean = text.strip()
    clean_lower = clean.lower()

    if len(clean) < 2:
        return False, label, False, False, []

    # 1. Filter out generic noise words and job titles across organizations
    if is_noise_or_job_title(clean_lower, label):
        return False, label, False, False, []

    # 2. Label normalization
    if label in ["phone number", "email address", "financial account"]:
        normalized_label = "identifier"
    elif label in ["person", "organization", "location", "date", "time", "identifier"]:
        normalized_label = label
    else:
        normalized_label = "identifier"

    # 3. Strict validation for identifiers: must not be plain English prose
    if normalized_label == "identifier":
        if not is_valid_identifier(clean):
            # Pure alphabetic word classified as identifier (e.g. "OFFICIAL work email", "Inbox") -> False positive
            return False, normalized_label, False, False, []

    # 4. Evaluate quality flags, low-confidence status, and source-image verification priority
    is_low_conf, req_verify, flags = evaluate_entity_quality(clean, normalized_label, confidence, ocr_confidence)

    return True, normalized_label, is_low_conf, req_verify, flags


def extract_entities_from_text(
    text: str,
    evidence_id: Optional[str] = None,
    filename: Optional[str] = None,
    threshold: float = 0.25,
    custom_labels: Optional[List[str]] = None,
    ocr_confidence: Optional[float] = None,
) -> List[ExtractedEntity]:
    """
    Extracts entities from text using GLiNER with regex augmentation and validation filters.
    Preserves questionable or low-confidence detections flagged with quality metrics.
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

                is_valid, normalized_label, is_low_conf, req_verify, flags = validate_and_filter_entity(
                    p_text, p_label, p_score, ocr_confidence
                )
                if not is_valid:
                    continue

                span_key = (p_text.lower(), normalized_label, abs_start, abs_end)
                if span_key not in seen_spans:
                    seen_spans.add(span_key)
                    extracted.append(
                        ExtractedEntity(
                            text=p_text,
                            label=normalized_label,
                            confidence=round(p_score, 4),
                            ocr_confidence=ocr_confidence,
                            start_char=abs_start,
                            end_char=abs_end,
                            evidence_id=evidence_id,
                            filename=filename,
                            is_low_confidence=is_low_conf,
                            requires_source_verification=req_verify,
                            quality_flags=flags,
                        )
                    )
        except Exception:
            pass

    # Regex supplements for emails (forensic certainty)
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
                    ocr_confidence=ocr_confidence,
                    start_char=m.start(),
                    end_char=m.end(),
                    evidence_id=evidence_id,
                    filename=filename,
                    is_low_confidence=False,
                    requires_source_verification=False,
                    quality_flags=[],
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
                    ocr_confidence=ocr_confidence,
                    start_char=m.start(),
                    end_char=m.end(),
                    evidence_id=evidence_id,
                    filename=filename,
                    is_low_confidence=False,
                    requires_source_verification=False,
                    quality_flags=[],
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
                    ocr_confidence=ocr_confidence,
                    start_char=m.start(),
                    end_char=m.end(),
                    evidence_id=evidence_id,
                    filename=filename,
                    is_low_confidence=False,
                    requires_source_verification=False,
                    quality_flags=[],
                )
            )

    return extracted

    # Sort by character position in document
    extracted.sort(key=lambda e: e.start_char)
    return extracted
