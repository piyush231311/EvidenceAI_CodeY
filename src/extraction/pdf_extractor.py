"""Hybrid PDF text & OCR extraction module for Evidence AI."""

import os
import io
import time
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import pypdf
import pypdfium2

from src.extraction.schemas import EvidenceSegment, SourceLocation


def extract_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extracts text page-by-page from a PDF document.
    Automatically detects scanned/empty pages and applies PaddleOCR fallback.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        Dict with 'text', 'confidence', 'segments', 'metadata', 'processing_time_ms', 'success'.
    """
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    t_start = time.perf_counter()
    segments: List[EvidenceSegment] = []
    scanned_pages: List[int] = []
    text_pages: List[int] = []
    confidences: List[float] = []

    reader = pypdf.PdfReader(str(pdf_path))
    pdfium_doc = pypdfium2.PdfDocument(str(pdf_path))
    total_pages = len(reader.pages)

    # Extract PDF document metadata
    doc_meta = {}
    if reader.metadata:
        for k, v in reader.metadata.items():
            if v:
                doc_meta[str(k).lstrip("/")] = str(v)

    # Lazy OCR loader
    ocr_func = None

    for page_num in range(1, total_pages + 1):
        page_idx = page_num - 1
        page = reader.pages[page_idx]
        extracted_page_text = (page.extract_text() or "").strip()

        if len(extracted_page_text) >= 15:  # Sufficient digital text present
            text_pages.append(page_num)
            confidences.append(1.0)
            segments.append(
                EvidenceSegment(
                    segment_id=f"page-{page_num}",
                    text=extracted_page_text,
                    location=SourceLocation(page_number=page_num),
                    confidence=1.0,
                    is_ocr=False,
                )
            )
        else:
            # Page appears scanned or contains only images -> render and run PaddleOCR
            scanned_pages.append(page_num)
            if ocr_func is None:
                from src.extraction.ocr import extract_text_from_image
                ocr_func = extract_text_from_image

            try:
                page_pdfium = pdfium_doc[page_idx]
                pil_image = page_pdfium.render(scale=2.0).to_pil()
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                    pil_image.save(tmp_img.name, format="PNG")
                    tmp_img_path = tmp_img.name

                try:
                    ocr_result = ocr_func(tmp_img_path)
                    ocr_text = ocr_result.get("text", "").strip()
                    ocr_conf = float(ocr_result.get("confidence", 0.85))
                    confidences.append(ocr_conf)

                    lines = ocr_result.get("lines", [])
                    if lines:
                        for line_idx, line_info in enumerate(lines, 1):
                            segments.append(
                                EvidenceSegment(
                                    segment_id=f"page-{page_num}-line-{line_idx}",
                                    text=line_info.get("text", ""),
                                    location=SourceLocation(
                                        page_number=page_num,
                                        line_number=line_idx,
                                        bbox=line_info.get("bbox"),
                                    ),
                                    confidence=float(line_info.get("confidence", ocr_conf)),
                                    is_ocr=True,
                                )
                            )
                    else:
                        segments.append(
                            EvidenceSegment(
                                segment_id=f"page-{page_num}",
                                text=ocr_text,
                                location=SourceLocation(page_number=page_num),
                                confidence=ocr_conf,
                                is_ocr=True,
                            )
                        )
                finally:
                    if os.path.exists(tmp_img_path):
                        os.remove(tmp_img_path)
            except Exception as ocr_err:
                # Fallback to whatever minimal text was extracted
                confidences.append(0.5)
                segments.append(
                    EvidenceSegment(
                        segment_id=f"page-{page_num}",
                        text=extracted_page_text,
                        location=SourceLocation(page_number=page_num),
                        confidence=0.5,
                        is_ocr=False,
                    )
                )

    full_text = "\n\n".join([f"--- Page {s.location.page_number} ---\n{s.text}" for s in segments if s.text])
    overall_conf = round(sum(confidences) / len(confidences), 4) if confidences else 1.0
    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return {
        "text": full_text,
        "confidence": overall_conf,
        "segments": [s.model_dump() for s in segments],
        "metadata": {
            "total_pages": total_pages,
            "text_pages": text_pages,
            "scanned_pages": scanned_pages,
            "document_metadata": doc_meta,
            "engine": "Hybrid PyPDF + PaddleOCR",
        },
        "processing_time_ms": elapsed_ms,
        "success": True,
    }
