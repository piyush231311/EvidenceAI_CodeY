"""Structured text, chat logs, CSV, and email extraction module for Evidence AI."""

import os
import re
import csv
import json
import time
import email
from email import policy
from pathlib import Path
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from src.extraction.schemas import EvidenceSegment, SourceLocation


# Regex patterns for timestamped chat log exports
CHAT_LINE_PATTERNS = [
    # [2026-05-12 14:32:00] Alice: message or [14:32:00] Alice: message
    re.compile(r"^\[(?P<ts>[^\]]+)\]\s*(?P<sender>[^:]+):\s*(?P<msg>.*)$"),
    # 12/05/2026, 14:32 - Alice: message or 5/12/26, 2:32 PM - Alice: message
    re.compile(r"^(?P<ts>\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\s*[-:]\s*(?P<sender>[^:]+):\s*(?P<msg>.*)$"),
    # Alice [2026-05-12 14:32]: message
    re.compile(r"^(?P<sender>[^\[:]+)\s*\[(?P<ts>[^\]]+)\]:\s*(?P<msg>.*)$"),
]


def extract_eml(eml_path: str) -> Dict[str, Any]:
    """
    Extracts structured email metadata, headers, and body from an .eml file.
    """
    eml_path = Path(eml_path).resolve()
    t_start = time.perf_counter()

    with open(eml_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    subject = str(msg.get("Subject", "")).strip()
    sender = str(msg.get("From", "")).strip()
    recipient = str(msg.get("To", "")).strip()
    cc = str(msg.get("Cc", "")).strip()
    date = str(msg.get("Date", "")).strip()
    msg_id = str(msg.get("Message-ID", "")).strip()

    body_text = ""
    # Extract plain body first, or HTML fallback
    plain_part = msg.get_body(preferencelist=("plain",))
    if plain_part:
        body_text = plain_part.get_content()
    else:
        html_part = msg.get_body(preferencelist=("html",))
        if html_part:
            soup = BeautifulSoup(html_part.get_content(), "html.parser")
            body_text = soup.get_text(separator="\n").strip()

    header_block = (
        f"From: {sender}\n"
        f"To: {recipient}\n"
        + (f"Cc: {cc}\n" if cc else "")
        + f"Date: {date}\n"
        f"Subject: {subject}\n"
        f"Message-ID: {msg_id}\n\n"
    )
    full_text = header_block + body_text.strip()

    segments = [
        EvidenceSegment(
            segment_id="email-headers",
            text=header_block.strip(),
            location=SourceLocation(sender=sender, timestamp=date),
            confidence=1.0,
            is_ocr=False,
        ),
        EvidenceSegment(
            segment_id="email-body",
            text=body_text.strip(),
            location=SourceLocation(sender=sender, timestamp=date),
            confidence=1.0,
            is_ocr=False,
        ),
    ]

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
    return {
        "text": full_text,
        "confidence": 1.0,
        "segments": [s.model_dump() for s in segments],
        "metadata": {
            "from": sender,
            "to": recipient,
            "cc": cc,
            "date": date,
            "subject": subject,
            "message_id": msg_id,
            "engine": "email.policy.default + BeautifulSoup4",
        },
        "processing_time_ms": elapsed_ms,
        "success": True,
    }


def extract_json_chat(json_path: str) -> Dict[str, Any]:
    """
    Extracts structured messages from JSON chat exports.
    Handles list of messages or dict with 'messages' key.
    """
    json_path = Path(json_path).resolve()
    t_start = time.perf_counter()

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        with open(json_path, "r", encoding="latin-1") as f:
            data = json.load(f)

    messages = []
    if isinstance(data, list):
        messages = data
    elif isinstance(data, dict):
        for key in ["messages", "chat", "conversation", "records", "data"]:
            if key in data and isinstance(data[key], list):
                messages = data[key]
                break

    segments: List[EvidenceSegment] = []
    text_lines: List[str] = []

    if messages:
        for idx, item in enumerate(messages, 1):
            if isinstance(item, dict):
                # Common message keys
                sender = str(item.get("sender") or item.get("from") or item.get("author") or item.get("user") or "")
                ts = str(item.get("timestamp") or item.get("time") or item.get("date") or item.get("datetime") or "")
                txt = str(item.get("text") or item.get("message") or item.get("content") or item.get("body") or "")

                if not txt and "body" in item:
                    txt = str(item["body"])

                msg_repr = f"[{ts}] {sender}: {txt}" if (ts or sender) else txt
                text_lines.append(msg_repr)

                segments.append(
                    EvidenceSegment(
                        segment_id=f"msg-{idx}",
                        text=txt or msg_repr,
                        location=SourceLocation(sender=sender or None, timestamp=ts or None, line_number=idx),
                        confidence=1.0,
                        is_ocr=False,
                    )
                )
            else:
                str_item = str(item)
                text_lines.append(str_item)
                segments.append(
                    EvidenceSegment(
                        segment_id=f"item-{idx}",
                        text=str_item,
                        location=SourceLocation(line_number=idx),
                        confidence=1.0,
                        is_ocr=False,
                    )
                )
        full_text = "\n".join(text_lines)
    else:
        # Generic JSON serialization
        full_text = json.dumps(data, indent=2)
        segments.append(
            EvidenceSegment(
                segment_id="json-root",
                text=full_text,
                location=SourceLocation(),
                confidence=1.0,
                is_ocr=False,
            )
        )

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
    return {
        "text": full_text,
        "confidence": 1.0,
        "segments": [s.model_dump() for s in segments],
        "metadata": {
            "message_count": len(messages),
            "engine": "JSON Structured Parser",
        },
        "processing_time_ms": elapsed_ms,
        "success": True,
    }


def extract_csv(csv_path: str) -> Dict[str, Any]:
    """
    Extracts tabular rows and field columns from CSV evidence logs.
    """
    csv_path = Path(csv_path).resolve()
    t_start = time.perf_counter()

    rows: List[Dict[str, str]] = []
    fieldnames: List[str] = []

    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            rows = list(reader)
    except Exception:
        with open(csv_path, "r", encoding="latin-1", errors="replace") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            rows = list(reader)

    segments: List[EvidenceSegment] = []
    text_lines: List[str] = []

    if fieldnames:
        text_lines.append(" | ".join(fieldnames))

    for r_idx, row in enumerate(rows, 1):
        row_str = " | ".join([f"{k}: {v}" for k, v in row.items() if v])
        text_lines.append(row_str)

        # Detect sender or timestamp fields
        sender_val = None
        ts_val = None
        for k, v in row.items():
            kl = k.lower()
            if any(term in kl for term in ["sender", "from", "author", "user"]):
                sender_val = v
            if any(term in kl for term in ["time", "date", "created", "timestamp"]):
                ts_val = v

        segments.append(
            EvidenceSegment(
                segment_id=f"row-{r_idx}",
                text=row_str,
                location=SourceLocation(row_index=r_idx, sender=sender_val, timestamp=ts_val),
                confidence=1.0,
                is_ocr=False,
            )
        )

    full_text = "\n".join(text_lines)
    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return {
        "text": full_text,
        "confidence": 1.0,
        "segments": [s.model_dump() for s in segments],
        "metadata": {
            "row_count": len(rows),
            "columns": fieldnames,
            "engine": "csv.DictReader",
        },
        "processing_time_ms": elapsed_ms,
        "success": True,
    }


def extract_txt_chat(txt_path: str) -> Dict[str, Any]:
    """
    Extracts plain text or timestamped chat logs from a .txt file.
    """
    txt_path = Path(txt_path).resolve()
    t_start = time.perf_counter()

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(txt_path, "r", encoding="latin-1", errors="replace") as f:
            lines = f.readlines()

    segments: List[EvidenceSegment] = []
    raw_lines: List[str] = []

    for idx, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue

        raw_lines.append(line)
        sender = None
        timestamp = None

        # Check for chat line match
        for pat in CHAT_LINE_PATTERNS:
            m = pat.match(line)
            if m:
                groups = m.groupdict()
                sender = groups.get("sender", "").strip() or None
                timestamp = groups.get("ts", "").strip() or None
                break

        segments.append(
            EvidenceSegment(
                segment_id=f"line-{idx}",
                text=line,
                location=SourceLocation(line_number=idx, sender=sender, timestamp=timestamp),
                confidence=1.0,
                is_ocr=False,
            )
        )

    full_text = "\n".join(raw_lines)
    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return {
        "text": full_text,
        "confidence": 1.0,
        "segments": [s.model_dump() for s in segments],
        "metadata": {
            "line_count": len(segments),
            "engine": "Regex Chat & Plain Text Parser",
        },
        "processing_time_ms": elapsed_ms,
        "success": True,
    }
