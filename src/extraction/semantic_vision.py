"""
Evidence AI — Semantic Image Understanding Adapter (Qwen3-VL via Ollama).

Complements PaddleOCR by analyzing the visual and semantic content of evidence images:
  - Content classification: meme | social_post | chat | document | photo | other | uncertain
  - Directly visible elements (objects, layout, posture, composition)
  - Meme indicators (reaction faces, caption bars, humorous/ironic juxtaposition)
  - Social-media & chat interface context (handles, story timers, view counts, admin toolbars)
  - Text-visual relationships (how overlaid captions relate to imagery)
  - Context missed by plain OCR
  - Explicit visual uncertainties (distinguishing observation from interpretation)

Strict Forensic Safeguards:
  - Never overwrites PaddleOCR text, segments, or SHA-256 hashes.
  - Never infers real people's legal identities from faces.
  - Never concludes criminal conduct, malicious intent, or lack of consent from imagery alone.
  - Caches results by (sha256, model_name, pipeline_version) to prevent redundant GPU runs.
"""

import base64
import hashlib
import io
import json
import logging
import os
import subprocess
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union
from PIL import Image
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VISION_CACHE_FILE = PROJECT_ROOT / "models_cache" / "vision_cache.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:4b-instruct")
DEFAULT_VISION_MODEL = OLLAMA_VISION_MODEL
VISION_PIPELINE_VERSION = "1.0.0"
VISION_MAX_IMAGE_EDGE = int(os.getenv("VISION_MAX_IMAGE_EDGE", "1024"))
VISION_TIMEOUT_SECONDS = int(os.getenv("VISION_TIMEOUT_SECONDS", "120"))

# Sequential GPU lock to prevent concurrent vision/text contention on 6 GB VRAM
_VISION_GPU_LOCK = threading.Lock()
_CACHE_LOCK = threading.Lock()

AllowedContentType = Literal[
    "meme", "social_post", "chat", "document", "photo", "other", "uncertain"
]
AllowedVisionStatus = Literal["completed", "failed", "skipped"]


class SemanticVisionObservation(BaseModel):
    """Validated structured output from semantic vision analysis of an evidence image."""
    evidence_id: str
    filename: str = ""
    sha256: str = ""
    content_type: AllowedContentType = "uncertain"
    visual_description: str = ""
    visual_elements: List[str] = Field(default_factory=list)
    meme_indicators: List[str] = Field(default_factory=list)
    social_media_context: List[str] = Field(default_factory=list)
    text_visual_relationships: List[str] = Field(default_factory=list)
    context_missed_by_plain_ocr: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    model_name: str = OLLAMA_VISION_MODEL
    pipeline_version: str = VISION_PIPELINE_VERSION
    status: AllowedVisionStatus = "completed"
    error_message: Optional[str] = None
    inference_time_ms: float = 0.0
    load_duration_ms: float = 0.0
    vram_used_mib: Optional[int] = None
    from_cache: bool = False
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def visual_category(self) -> str:
        return self.content_type

    @property
    def scene_summary(self) -> str:
        return self.visual_description

    @property
    def case_relevance(self) -> str:
        if self.context_missed_by_plain_ocr:
            return "; ".join(self.context_missed_by_plain_ocr[:2])
        if self.text_visual_relationships:
            return "; ".join(self.text_visual_relationships[:2])
        return self.visual_description

    @property
    def key_visual_facts(self) -> List[str]:
        return list(self.visual_elements[:3]) + list(self.context_missed_by_plain_ocr[:2])

    @property
    def confidence(self) -> float:
        return 0.92 if self.status == "completed" else 0.0

    @property
    def processing_time_ms(self) -> float:
        return self.inference_time_ms

    def to_dict(self) -> Dict[str, Any]:
        d = json.loads(self.model_dump_json())
        d["visual_category"] = self.visual_category
        d["scene_summary"] = self.scene_summary
        d["case_relevance"] = self.case_relevance
        d["key_visual_facts"] = self.key_visual_facts
        d["confidence"] = self.confidence
        d["processing_time_ms"] = self.processing_time_ms
        return d

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        d = super().model_dump(*args, **kwargs)
        d["visual_category"] = self.visual_category
        d["scene_summary"] = self.scene_summary
        d["case_relevance"] = self.case_relevance
        d["key_visual_facts"] = self.key_visual_facts
        d["confidence"] = self.confidence
        d["processing_time_ms"] = self.processing_time_ms
        return d

    @field_validator("content_type", mode="before")
    @classmethod
    def _normalize_content_type(cls, v: Any) -> str:
        if not isinstance(v, str):
            return "uncertain"
        val = v.strip().lower().replace("-", "_").replace(" ", "_")
        mapping = {
            "meme": "meme",
            "internet_meme": "meme",
            "social_post": "social_post",
            "social_media_post": "social_post",
            "story": "social_post",
            "instagram_story": "social_post",
            "chat": "chat",
            "chat_screenshot": "chat",
            "messaging": "chat",
            "group_chat": "chat",
            "document": "document",
            "form": "document",
            "slip": "document",
            "invoice": "document",
            "photo": "photo",
            "photograph": "photo",
            "other": "other",
            "uncertain": "uncertain",
        }
        return mapping.get(val, "uncertain")


def is_semantic_vision_enabled(override: Optional[bool] = None) -> bool:
    """Checks whether semantic vision analysis is enabled via override or environment variable."""
    if override is not None:
        return bool(override)
    env_val = os.getenv("EVIDENCE_AI_ENABLE_VISION", "1").strip().lower()
    return env_val not in ("0", "false", "no", "off", "disabled")


def query_gpu_vram_mib() -> Optional[Dict[str, int]]:
    """Queries NVIDIA GPU VRAM usage in MiB via nvidia-smi if available."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            text=True,
            timeout=2,
        ).strip()
        parts = [int(x.strip()) for x in out.splitlines()[0].split(",")]
        return {"total_mib": parts[0], "used_mib": parts[1], "free_mib": parts[2]}
    except Exception:
        return None


def check_vision_model_available(
    model_name: str = OLLAMA_VISION_MODEL,
    base_url: str = OLLAMA_BASE_URL,
) -> Dict[str, Any]:
    """Checks if Ollama is reachable and whether the requested vision model is installed."""
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/tags",
            headers={"User-Agent": "EvidenceAI-Vision"},
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            matched = next(
                (m for m in models if m == model_name or m.startswith(model_name.split(":")[0])),
                None,
            )
            return {
                "ollama_online": True,
                "model_available": bool(matched),
                "resolved_model": matched or model_name,
                "installed_models": models,
            }
    except Exception as exc:
        return {
            "ollama_online": False,
            "model_available": False,
            "resolved_model": model_name,
            "installed_models": [],
            "error": str(exc),
        }


def unload_ollama_model(model_name: str, base_url: str = OLLAMA_BASE_URL) -> bool:
    """Explicitly unloads an inactive Ollama model from VRAM (keep_alive=0) when switching models."""
    try:
        payload = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def _make_cache_key(sha256: str, model_name: str, pipeline_version: str = VISION_PIPELINE_VERSION) -> str:
    return f"{sha256}::{model_name}::{pipeline_version}"


def _load_cached_observation(
    sha256: str,
    model_name: str,
    evidence_id: str,
    filename: str,
) -> Optional[SemanticVisionObservation]:
    """Loads a cached SemanticVisionObservation from disk if available."""
    if not sha256 or not VISION_CACHE_FILE.exists():
        return None
    key = _make_cache_key(sha256, model_name, VISION_PIPELINE_VERSION)
    with _CACHE_LOCK:
        try:
            cache_data = json.loads(VISION_CACHE_FILE.read_text(encoding="utf-8"))
            entry = cache_data.get(key)
            if entry and entry.get("status") == "completed":
                obs = SemanticVisionObservation(**entry)
                obs.evidence_id = evidence_id
                obs.filename = filename or obs.filename
                obs.from_cache = True
                return obs
        except Exception as exc:
            logger.warning(f"Failed to read vision cache: {exc}")
    return None


def _save_cached_observation(obs: SemanticVisionObservation) -> None:
    """Persists a completed SemanticVisionObservation to the SHA-256 disk cache."""
    if not obs.sha256 or obs.status != "completed":
        return
    key = _make_cache_key(obs.sha256, obs.model_name, obs.pipeline_version)
    with _CACHE_LOCK:
        try:
            VISION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            cache_data: Dict[str, Any] = {}
            if VISION_CACHE_FILE.exists():
                try:
                    cache_data = json.loads(VISION_CACHE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    cache_data = {}
            cache_data[key] = json.loads(obs.model_dump_json())
            VISION_CACHE_FILE.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to write vision cache: {exc}")


def _encode_image_for_vlm(image_path: Union[str, Path], max_edge: int = VISION_MAX_IMAGE_EDGE) -> str:
    """
    Resizes high-resolution images in memory to a conservative max dimension (default 1024px)
    to bound VRAM usage on 6 GB GPUs without modifying the original file on disk.
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_edge:
            scale = max_edge / float(max(w, h))
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return base64.b64encode(buf.getvalue()).decode("utf-8")


VISION_SYSTEM_PROMPT = (
    "You are a neutral forensic visual evidence analyst for Evidence AI.\n"
    "Examine the supplied image and return ONLY valid JSON matching this exact structure:\n"
    "{\n"
    '  "content_type": "meme | social_post | chat | document | photo | other | uncertain",\n'
    '  "visual_description": "Detailed neutral description of what is visually depicted in the image",\n'
    '  "visual_elements": ["Directly visible objects, faces/expressions, layout, timestamps, icons, or stamps"],\n'
    '  "meme_indicators": ["Specific visual/textual cues if the image is or contains a meme (empty list if not a meme)"],\n'
    '  "social_media_context": ["Visible platform UI elements, account handles, story age, view counts, action toolbars, or chat headers"],\n'
    '  "text_visual_relationships": ["How visible captions, labels, or chat bubbles relate to the visual composition"],\n'
    '  "context_missed_by_plain_ocr": ["Visual meaning, UI controls, avatars, or layout hierarchy that plain text OCR cannot capture"],\n'
    '  "uncertainties": ["What cannot be reliably determined from the image alone (e.g. real legal identities, consent, intent, off-screen events)"]\n'
    "}\n"
    "CRITICAL FORENSIC RULES:\n"
    "1. Distinguish directly visible observations from interpretations.\n"
    "2. If an image is a social media story or post that contains a meme caption and reaction photo, set content_type to 'meme'.\n"
    "3. Do NOT identify real people's legal identities from faces alone.\n"
    "4. Do NOT conclude criminal guilt, malicious intent, or lack of consent from visual appearance alone."
)


def analyze_image_semantics(
    image_path: Optional[Union[str, Path]] = None,
    evidence_id: str = "",
    filename: str = "",
    sha256: Optional[str] = None,
    ocr_text_hint: Optional[str] = None,
    vision_enabled: Optional[bool] = None,
    force_refresh: bool = False,
    model_name: str = OLLAMA_VISION_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    file_path: Optional[Union[str, Path]] = None,
    ocr_text: Optional[str] = None,
) -> SemanticVisionObservation:
    """
    Runs Qwen3-VL semantic image analysis on an evidence image with SHA-256 caching,
    bounded timeouts, sequential GPU locking, and strict Pydantic validation.
    """
    resolved_path = image_path or file_path or ""
    path_obj = Path(resolved_path)
    fname = filename or path_obj.name
    ocr_hint = ocr_text_hint if ocr_text_hint is not None else ocr_text

    # Compute SHA-256 if not provided
    if not sha256 and path_obj.exists() and path_obj.is_file():
        h = hashlib.sha256()
        with open(path_obj, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        sha256 = h.hexdigest()
    sha256 = sha256 or ""

    # 1. Check feature flag
    if not is_semantic_vision_enabled(vision_enabled):
        return SemanticVisionObservation(
            evidence_id=evidence_id,
            filename=fname,
            sha256=sha256,
            content_type="uncertain",
            visual_description="Semantic vision analysis was skipped because vision processing is disabled.",
            model_name=model_name,
            status="skipped",
        )

    # 2. Check SHA-256 cache first (unless force_refresh=True)
    if not force_refresh and sha256:
        cached = _load_cached_observation(sha256, model_name, evidence_id, fname)
        if cached:
            return cached

    # 3. Verify file exists on disk
    if not path_obj.exists() or not path_obj.is_file():
        return SemanticVisionObservation(
            evidence_id=evidence_id,
            filename=fname,
            sha256=sha256,
            content_type="uncertain",
            status="failed",
            error_message=f"Image file not found on disk: {path_obj}",
            model_name=model_name,
        )

    # 4. Check Ollama & vision model availability
    avail = check_vision_model_available(model_name=model_name, base_url=base_url)
    if not avail.get("ollama_online"):
        return SemanticVisionObservation(
            evidence_id=evidence_id,
            filename=fname,
            sha256=sha256,
            content_type="uncertain",
            status="failed",
            error_message=f"Ollama server unreachable at {base_url}: {avail.get('error', 'connection refused')}",
            model_name=model_name,
        )
    if not avail.get("model_available"):
        return SemanticVisionObservation(
            evidence_id=evidence_id,
            filename=fname,
            sha256=sha256,
            content_type="uncertain",
            status="failed",
            error_message=f"Vision model '{model_name}' is not installed in Ollama (installed: {avail.get('installed_models')}).",
            model_name=model_name,
        )

    resolved_model = avail.get("resolved_model", model_name)

    # 5. Execute inference sequentially under _VISION_GPU_LOCK
    with _VISION_GPU_LOCK:
        t0 = time.time()
        try:
            b64_img = _encode_image_for_vlm(path_obj, max_edge=VISION_MAX_IMAGE_EDGE)
            user_prompt = (
                f"Evidence Filename: {fname}\n"
                "Analyze this evidence image according to the JSON schema. "
                "Describe what type of image it is, what is visually shown, whether it contains a meme, "
                "how visible text relates to the visual composition, relevant social-media or document interface elements, "
                "visible context that plain OCR would miss, and what cannot be reliably determined from the image alone."
            )

            payload = {
                "model": resolved_model,
                "messages": [
                    {"role": "system", "content": VISION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt, "images": [b64_img]},
                ],
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 4096,
                },
            }

            req = urllib.request.Request(
                f"{base_url.rstrip('/')}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=VISION_TIMEOUT_SECONDS) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            elapsed_ms = (time.time() - t0) * 1000.0
            load_ms = float(resp_data.get("load_duration", 0)) / 1e6
            vram_info = query_gpu_vram_mib()
            vram_used = vram_info.get("used_mib") if vram_info else None

            raw_content = resp_data.get("message", {}).get("content", "").strip()
            if not raw_content:
                raise ValueError("Empty response content returned by Qwen3-VL.")

            parsed = json.loads(raw_content)

            # Determine content_type: if meme_indicators are substantive and content_type was social_post, classify as meme
            raw_ct = parsed.get("content_type", "uncertain")
            meme_inds = [str(x).strip() for x in parsed.get("meme_indicators", []) if str(x).strip()]
            vis_desc = str(parsed.get("visual_description", "")).strip()
            if not vis_desc:
                raise ValueError("Vision model returned an empty visual_description.")

            if raw_ct in ("social_post", "photo", "other") and len(meme_inds) >= 2 and "meme" in vis_desc.lower():
                raw_ct = "meme"

            obs = SemanticVisionObservation(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                content_type=raw_ct,
                visual_description=vis_desc,
                visual_elements=[str(x).strip() for x in parsed.get("visual_elements", []) if str(x).strip()],
                meme_indicators=meme_inds,
                social_media_context=[str(x).strip() for x in parsed.get("social_media_context", []) if str(x).strip()],
                text_visual_relationships=[str(x).strip() for x in parsed.get("text_visual_relationships", []) if str(x).strip()],
                context_missed_by_plain_ocr=[str(x).strip() for x in parsed.get("context_missed_by_plain_ocr", []) if str(x).strip()],
                uncertainties=[str(x).strip() for x in parsed.get("uncertainties", []) if str(x).strip()],
                model_name=resolved_model,
                pipeline_version=VISION_PIPELINE_VERSION,
                status="completed",
                inference_time_ms=round(elapsed_ms, 1),
                load_duration_ms=round(load_ms, 1),
                vram_used_mib=vram_used,
                from_cache=False,
            )

            _save_cached_observation(obs)
            return obs

        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1000.0
            logger.error(f"Semantic vision analysis failed for {fname} ({evidence_id}): {exc}")
            return SemanticVisionObservation(
                evidence_id=evidence_id,
                filename=fname,
                sha256=sha256,
                content_type="uncertain",
                visual_description="",
                model_name=resolved_model,
                pipeline_version=VISION_PIPELINE_VERSION,
                status="failed",
                error_message=str(exc),
                inference_time_ms=round(elapsed_ms, 1),
                from_cache=False,
            )
