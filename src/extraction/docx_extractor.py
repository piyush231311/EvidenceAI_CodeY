"""DOCX text & table extraction module for Evidence AI using python-docx."""

import time
from pathlib import Path
from typing import Any, Dict, List
import docx

from src.extraction.schemas import EvidenceSegment, SourceLocation


def extract_docx(docx_path: str) -> Dict[str, Any]:
    """
    Extracts paragraphs, tables, and metadata from a Microsoft Word .docx file.

    Args:
        docx_path: Absolute or relative path to the .docx file.

    Returns:
        Dict with 'text', 'confidence', 'segments', 'metadata', 'processing_time_ms', 'success'.
    """
    docx_path = Path(docx_path).resolve()
    if not docx_path.is_file():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")

    t_start = time.perf_counter()
    doc = docx.Document(str(docx_path))
    segments: List[EvidenceSegment] = []
    text_blocks: List[str] = []

    # Extract core properties
    core_props = {}
    try:
        props = doc.core_properties
        if props.author:
            core_props["author"] = props.author
        if props.title:
            core_props["title"] = props.title
        if props.created:
            core_props["created"] = props.created.isoformat()
        if props.modified:
            core_props["modified"] = props.modified.isoformat()
    except Exception:
        pass

    # Extract paragraphs
    para_count = 0
    for p_idx, para in enumerate(doc.paragraphs, 1):
        txt = para.text.strip()
        if txt:
            para_count += 1
            segments.append(
                EvidenceSegment(
                    segment_id=f"para-{p_idx}",
                    text=txt,
                    location=SourceLocation(paragraph_index=p_idx),
                    confidence=1.0,
                    is_ocr=False,
                )
            )
            text_blocks.append(txt)

    # Extract tables
    table_count = len(doc.tables)
    for t_idx, table in enumerate(doc.tables, 1):
        table_rows_text = []
        for r_idx, row in enumerate(table.rows, 1):
            row_cells = [cell.text.strip() for cell in row.cells]
            if any(row_cells):
                row_str = " | ".join(row_cells)
                table_rows_text.append(row_str)
                segments.append(
                    EvidenceSegment(
                        segment_id=f"table-{t_idx}-row-{r_idx}",
                        text=row_str,
                        location=SourceLocation(table_index=t_idx, row_index=r_idx),
                        confidence=1.0,
                        is_ocr=False,
                    )
                )
        if table_rows_text:
            text_blocks.append(f"[Table {t_idx}]\n" + "\n".join(table_rows_text))

    full_text = "\n\n".join(text_blocks)
    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return {
        "text": full_text,
        "confidence": 1.0,
        "segments": [s.model_dump() for s in segments],
        "metadata": {
            "paragraph_count": para_count,
            "table_count": table_count,
            "core_properties": core_props,
            "engine": "python-docx",
        },
        "processing_time_ms": elapsed_ms,
        "success": True,
    }
