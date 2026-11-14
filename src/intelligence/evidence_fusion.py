"""
Evidence AI — Multi-Modal Evidence Fusion Layer.

Combines:
  - Normalized PaddleOCR text (image screenshots)
  - Faster-Whisper audio transcriptions
  - Document text (PDF, DOCX, EML, JSON, CSV, TXT)
  - Qwen3-VL semantic visual observations (visual descriptions, meme indicators,
    social-media UI controls, text-visual relationships, context missed by plain OCR)
  - GLiNER / RapidFuzz entities
  - Chronological event candidates & timeline entries
  - Provenance metadata (evidence_id, filename, sha256) and extraction uncertainties

Strict Separation & Deduplication Rules:
  - Never overwrites or pollutes OCR/ASR transcripts with VLM descriptions.
  - Deduplicates verbatim text already captured by PaddleOCR from visual bullet lists
    while preserving visual layout, meme framing, and UI context.
  - Explicitly tracks whether visual understanding is complete, partial, failed, or skipped.
"""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.extraction.semantic_vision import SemanticVisionObservation


class FusedEvidenceItem(BaseModel):
    """Single evidence item combining text/transcript extraction and semantic vision observations."""
    evidence_id: str
    filename: str
    file_type: str  # image | audio | text | pdf | docx | eml | json | csv
    sha256: str = ""
    extraction_confidence: Optional[float] = None
    # Strictly separated textual vs. visual modalities
    extracted_text: str = ""
    text_source_engine: str = "PaddleOCR / Whisper / DocParser"
    vision_observation: Optional[SemanticVisionObservation] = None
    deduplicated_visual_highlights: List[str] = Field(default_factory=list)
    combined_uncertainties: List[str] = Field(default_factory=list)


class UnifiedEvidenceContext(BaseModel):
    """Unified multi-modal case context passed into Qwen case understanding and report generation."""
    case_id: str
    items: List[FusedEvidenceItem] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    scheduled_events_count: int = 0
    unscheduled_events_count: int = 0
    vision_enabled: bool = True
    vision_status_summary: str = "not_applicable"  # complete | partial | failed | skipped | not_applicable
    images_total: int = 0
    images_completed: int = 0
    images_failed: int = 0
    images_skipped: int = 0
    vision_errors: List[str] = Field(default_factory=list)


def _deduplicate_visual_against_ocr(ocr_text: str, visual_obs: SemanticVisionObservation) -> List[str]:
    """
    Produces a deduplicated list of semantic visual insights that add value beyond raw OCR text,
    preserving visual composition, meme indicators, UI controls, and text-visual relationships.
    """
    ocr_norm = re.sub(r"\s+", " ", (ocr_text or "").lower()).strip()
    highlights: List[str] = []
    seen_norm = set()

    candidates: List[str] = []
    if visual_obs.content_type and visual_obs.content_type != "uncertain":
        candidates.append(f"Visual Content Classification: {visual_obs.content_type}")
    if visual_obs.visual_description:
        candidates.append(f"Visual Scene: {visual_obs.visual_description}")
    for mi in visual_obs.meme_indicators:
        candidates.append(f"Meme Indicator: {mi}")
    for sm in visual_obs.social_media_context:
        candidates.append(f"Interface / Platform Context: {sm}")
    for tvr in visual_obs.text_visual_relationships:
        candidates.append(f"Text-Visual Relationship: {tvr}")
    for cm in visual_obs.context_missed_by_plain_ocr:
        candidates.append(f"Context Beyond Plain OCR: {cm}")
    for ve in visual_obs.visual_elements:
        # Skip pure text-overlay items if the exact string is already in OCR and has no visual framing words
        ve_low = ve.lower()
        if ve_low.startswith("text:") or ve_low.startswith("text overlay:"):
            raw_val = ve.split(":", 1)[-1].strip(" '\".").lower()
            if raw_val and raw_val in ocr_norm and len(ve.split()) < 8:
                continue
        candidates.append(f"Visible Element: {ve}")

    for cand in candidates:
        c_key = re.sub(r"[^a-z0-9]+", " ", cand.lower()).strip()
        if c_key and c_key not in seen_norm:
            seen_norm.add(c_key)
            highlights.append(cand)

    return highlights


def build_unified_evidence_context(
    case_id: str,
    evidence_items: List[Any],
    vision_observations: Optional[Dict[str, SemanticVisionObservation]] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Any]] = None,
    scheduled_events_count: int = 0,
    unscheduled_events_count: int = 0,
    vision_enabled: bool = True,
) -> UnifiedEvidenceContext:
    """
    Constructs the UnifiedEvidenceContext fusing OCR/ASR/Doc text with Qwen3-VL visual observations.
    """
    vision_observations = vision_observations or {}
    fused_items: List[FusedEvidenceItem] = []

    images_total = 0
    images_completed = 0
    images_failed = 0
    images_skipped = 0
    vision_errors: List[str] = []

    for item in evidence_items:
        if isinstance(item, dict):
            ev_id = str(item.get("id") or "")
            fname = str(item.get("original_filename") or item.get("filename") or "evidence_file")
            ftype = str(item.get("file_type") or "text")
            sha = str(item.get("sha256") or "")
            conf = item.get("extraction_confidence")
            txt = (item.get("extracted_text") or item.get("text") or "").strip()
            meta_raw = item.get("extraction_metadata")
        else:
            ev_id = str(getattr(item, "id", ""))
            fname = str(getattr(item, "original_filename", "evidence_file"))
            ftype = str(getattr(item, "file_type", "text"))
            sha = str(getattr(item, "sha256", "") or "")
            conf = getattr(item, "extraction_confidence", None)
            txt = (getattr(item, "extracted_text", "") or "").strip()
            meta_raw = getattr(item, "extraction_metadata", None)

        raw_vis = vision_observations.get(ev_id) if vision_enabled else None
        vis_obs: Optional[SemanticVisionObservation] = None
        if raw_vis is not None:
            if isinstance(raw_vis, SemanticVisionObservation):
                vis_obs = raw_vis
            elif isinstance(raw_vis, dict):
                try:
                    allowed_keys = set(SemanticVisionObservation.model_fields.keys())
                    vis_obs = SemanticVisionObservation(**{k: v for k, v in raw_vis.items() if k in allowed_keys})
                except Exception:
                    vis_obs = None

        if vision_enabled and not vis_obs and meta_raw:
            try:
                meta_dict = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                if isinstance(meta_dict, dict) and "semantic_vision" in meta_dict:
                    sv_raw = meta_dict["semantic_vision"]
                    if isinstance(sv_raw, dict):
                        allowed_keys = set(SemanticVisionObservation.model_fields.keys())
                        vis_obs = SemanticVisionObservation(**{k: v for k, v in sv_raw.items() if k in allowed_keys})
            except Exception:
                pass

        engine_name = (
            "PaddleOCR PP-OCRv6_small" if ftype == "image"
            else ("Faster-Whisper Small" if ftype == "audio" else "Unified Document Parser")
        )

        dedup_highlights: List[str] = []
        combined_uncert: List[str] = []

        if ftype == "image":
            images_total += 1
            if vis_obs:
                if vis_obs.status == "completed":
                    images_completed += 1
                    dedup_highlights = _deduplicate_visual_against_ocr(txt, vis_obs)
                    combined_uncert.extend(vis_obs.uncertainties)
                elif vis_obs.status == "failed":
                    images_failed += 1
                    err_msg = f"{fname}: {vis_obs.error_message or 'Vision analysis failed'}"
                    vision_errors.append(err_msg)
                    combined_uncert.append(f"Visual semantic analysis failed for {fname} ({vis_obs.error_message}); relying on OCR text only.")
                else:
                    images_skipped += 1
            else:
                if not vision_enabled:
                    images_skipped += 1
                else:
                    images_skipped += 1

        fused_items.append(
            FusedEvidenceItem(
                evidence_id=ev_id,
                filename=fname,
                file_type=ftype,
                sha256=sha,
                extraction_confidence=conf,
                extracted_text=txt,
                text_source_engine=engine_name,
                vision_observation=vis_obs,
                deduplicated_visual_highlights=dedup_highlights,
                combined_uncertainties=combined_uncert,
            )
        )

    if images_total == 0:
        vis_summary = "not_applicable"
    elif not vision_enabled or images_skipped == images_total:
        vis_summary = "skipped"
    elif images_completed == images_total:
        vis_summary = "complete"
    elif images_completed > 0:
        vis_summary = "partial"
    else:
        vis_summary = "failed"

    ev_dicts: List[Dict[str, Any]] = []
    for e in (events or []):
        if isinstance(e, dict):
            ev_dicts.append(e)
        elif hasattr(e, "model_dump"):
            ev_dicts.append(e.model_dump())
        else:
            ev_dicts.append({
                "event_id": getattr(e, "event_id", ""),
                "title": getattr(e, "title", ""),
                "description": getattr(e, "description", ""),
                "original_time_expression": getattr(e, "original_time_expression", None),
                "evidence_ids": getattr(e, "evidence_ids", []),
            })

    return UnifiedEvidenceContext(
        case_id=case_id,
        items=fused_items,
        entities=entities or [],
        events=ev_dicts,
        scheduled_events_count=scheduled_events_count,
        unscheduled_events_count=unscheduled_events_count,
        vision_enabled=vision_enabled,
        vision_status_summary=vis_summary,
        images_total=images_total,
        images_completed=images_completed,
        images_failed=images_failed,
        images_skipped=images_skipped,
        vision_errors=vision_errors,
    )


def format_fused_context_for_qwen(ctx: UnifiedEvidenceContext) -> str:
    """
    Formats the UnifiedEvidenceContext into a structured, provenance-preserving prompt
    for the single Qwen case-understanding pass.
    Clearly separates [OCR / AUDIO TRANSCRIPT] from [VISUAL SEMANTIC OBSERVATION — Qwen3-VL].
    """
    blocks: List[str] = []
    for idx, item in enumerate(ctx.items, 1):
        header = (
            f"=== EVIDENCE ITEM #{idx} ===\n"
            f"Evidence ID: {item.evidence_id}\n"
            f"Filename: {item.filename}\n"
            f"Modality: {item.file_type.upper()} (SHA-256: {item.sha256[:16]}...)\n"
        )
        text_section = (
            f"[{item.text_source_engine} VERBATIM TEXT]:\n"
            f"\"\"\"\n{item.extracted_text[:1800]}\n\"\"\"\n"
        )
        vis_section = ""
        if item.vision_observation and item.vision_observation.status == "completed":
            vo = item.vision_observation
            vis_lines = [
                f"[VISUAL SEMANTIC OBSERVATION — {vo.model_name} (status=completed, type={vo.content_type})]:",
                f"  • Visual Description: {vo.visual_description}",
            ]
            if vo.meme_indicators:
                vis_lines.append("  • Meme Indicators: " + "; ".join(vo.meme_indicators[:4]))
            if vo.social_media_context:
                vis_lines.append("  • Social Media / UI Context: " + "; ".join(vo.social_media_context[:5]))
            if vo.text_visual_relationships:
                vis_lines.append("  • Text-Visual Relationships: " + "; ".join(vo.text_visual_relationships[:3]))
            if vo.context_missed_by_plain_ocr:
                vis_lines.append("  • Visual Context Missed by Plain OCR: " + "; ".join(vo.context_missed_by_plain_ocr[:3]))
            if vo.uncertainties:
                vis_lines.append("  • Visual Uncertainties: " + "; ".join(vo.uncertainties[:3]))
            vis_section = "\n".join(vis_lines) + "\n"
        elif item.file_type == "image" and item.vision_observation and item.vision_observation.status == "failed":
            vis_section = (
                f"[VISUAL SEMANTIC OBSERVATION — status=FAILED]:\n"
                f"  • Error: {item.vision_observation.error_message}\n"
            )
        blocks.append(header + text_section + vis_section)

    if ctx.events:
        ev_lines = ["=== CHRONOLOGICAL EXTRACTED EVENTS ==="]
        for ev in ctx.events[:10]:
            t_str = ev.get("original_time_expression") or ev.get("normalized_start_time") or "Unscheduled"
            ev_lines.append(f"  • [{t_str}] {ev.get('title')}: {ev.get('description')} (Sources: {ev.get('evidence_ids')})")
        blocks.append("\n".join(ev_lines))

    return "\n\n".join(blocks)
