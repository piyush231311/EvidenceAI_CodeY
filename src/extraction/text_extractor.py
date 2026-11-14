"""Text & Document extraction module for Evidence AI (TXT, JSON, CSV, EML, PDF)."""

import os
import time
import email
from email import policy
from pathlib import Path
from typing import Any, Dict, Union

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".json", ".csv", ".eml", ".pdf"}


def extract_text_from_document(document_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract readable text content from text files, logs, emails, and PDFs.

    Args:
        document_path: Path to .txt, .json, .csv, .eml, or .pdf file.

    Returns:
        Dict containing:
            - 'text': Extracted full text content.
            - 'confidence': Confidence score (1.0 for direct digital text).
            - 'metadata': Format-specific parsing metadata.
            - 'processing_time_ms': Parsing time in milliseconds.
            - 'success': Boolean.
    """
    document_path = Path(document_path).resolve()

    if not document_path.is_file():
        raise FileNotFoundError(f"Document file not found: {document_path}")

    ext = document_path.suffix.lower()
    if ext not in SUPPORTED_TEXT_EXTENSIONS:
        raise ValueError(
            f"Unsupported text format '{ext}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_TEXT_EXTENSIONS))}"
        )

    t_start = time.perf_counter()
    extracted_text = ""
    metadata: Dict[str, Any] = {"format": ext}

    if ext == ".pdf":
        import pypdfium2
        pdf = pypdfium2.PdfDocument(str(document_path))
        pages_text = []
        for page_idx, page in enumerate(pdf):
            text_page = page.get_textpage()
            page_content = text_page.get_text_range()
            if page_content.strip():
                pages_text.append(f"--- Page {page_idx + 1} ---\n{page_content.strip()}")
        extracted_text = "\n\n".join(pages_text)
        metadata["page_count"] = len(pdf)

    elif ext == ".eml":
        with open(document_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
            subject = msg.get("Subject", "(No Subject)")
            sender = msg.get("From", "(Unknown Sender)")
            recipient = msg.get("To", "(Unknown Recipient)")
            date = msg.get("Date", "(Unknown Date)")

            body = msg.get_body(preferencelist=("plain", "html"))
            body_text = body.get_content() if body else ""

            extracted_text = (
                f"From: {sender}\n"
                f"To: {recipient}\n"
                f"Date: {date}\n"
                f"Subject: {subject}\n\n"
                f"{body_text}"
            )
            metadata["subject"] = subject
            metadata["from"] = sender
            metadata["date"] = date

    else:
        # .txt, .json, .csv
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
        except UnicodeDecodeError:
            with open(document_path, "r", encoding="latin-1", errors="replace") as f:
                extracted_text = f.read()

        metadata["char_count"] = len(extracted_text)

    proc_time_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return {
        "text": extracted_text.strip(),
        "confidence": 1.0,
        "metadata": metadata,
        "processing_time_ms": proc_time_ms,
        "success": True,
    }
