"""
Evidence AI — Image Synthetic Content Detector (Sentry ConvNeXt-Small Adapter).

Forensic detection of AI-generated, diffusion, and GAN image artifacts based on
Sentry ConvNeXt-Small (InfImagine/Sentry_image_models, Apache 2.0).

Core Forensic Principles:
  - Canonical Authenticity Outcomes:
      SYNTHETIC_INDICATORS_DETECTED: Model found strong synthetic artifacts.
      NO_STRONG_SYNTHETIC_INDICATORS: Model did not find strong synthetic artifacts (does not prove authenticity).
      INCONCLUSIVE: Result is ambiguous, borderline, or uncalibrated.
      UNSUPPORTED: File format or size cannot be assessed.
      DETECTION_FAILED: Inference did not complete due to execution or file error.
  - Image Distinction Taxonomy:
      A. AI-generated image file (synthesized by a generative model).
      B. Genuine screenshot of AI-generated content (e.g. social media meme capture).
      C. AI-generated screenshot simulating a genuine chat (synthetic UI).
      D. Real screenshot of a genuine chat (authentic app capture).
    Binary classifiers evaluate local textures and frequency distributions; they do NOT
    prove whether a chat screenshot represents an authentic real-world conversation.
  - Non-Suppression Rule: Synthetic warnings NEVER permanently delete or suppress evidence.
  - Provenance: Cryptographic C2PA / JUMBF and EXIF inspection included.
"""

import io
import json
import logging
import os
import re
import threading
import time
import types
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from PIL import Image
import torch
from pydantic import BaseModel, Field

from src.detection.provenance_checker import inspect_media_provenance, ProvenanceCheckResult

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGE_AUTH_CACHE_FILE = PROJECT_ROOT / "models_cache" / "image_authenticity_cache.json"

MODEL_IDENTIFIER = "sentry-convnext-small"
MODEL_VERSION = "5.1.0"
SENTRY_HF_REPO = "InfImagine/Sentry_image_models"
SENTRY_SUBPATH = "convnext_small_4xb256_fake5m_lr6e-4_10epoch/epoch_5.pth"

_IMAGE_DETECTOR_LOCK = threading.Lock()
_CACHE_LOCK = threading.Lock()
_LOADED_MODEL = None
_MODEL_DEVICE = "cpu"

CanonicalAssessment = Literal[
    "SYNTHETIC_INDICATORS_DETECTED",
    "NO_STRONG_SYNTHETIC_INDICATORS",
    "INCONCLUSIVE",
    "UNSUPPORTED",
    "DETECTION_FAILED",
]
CanonicalProcessingStatus = Literal[
    "COMPLETED", "FAILED", "SKIPPED", "INCONCLUSIVE", "UNSUPPORTED"
]


def normalize_assessment(val: str) -> CanonicalAssessment:
    """Normalizes assessment strings to canonical uppercase format."""
    v = (val or "").strip().upper()
    if v in ["SYNTHETIC_INDICATORS_DETECTED", "SYNTHETIC_DETECTED"]:
        return "SYNTHETIC_INDICATORS_DETECTED"
    if v in ["NO_STRONG_SYNTHETIC_INDICATORS", "SYNTHETIC_INDICATORS_NOT_DETECTED", "NOT_DETECTED"]:
        return "NO_STRONG_SYNTHETIC_INDICATORS"
    if v in ["UNSUPPORTED"]:
        return "UNSUPPORTED"
    if v in ["DETECTION_FAILED", "FAILED"]:
        return "DETECTION_FAILED"
    return "INCONCLUSIVE"


def normalize_processing_status(val: str) -> CanonicalProcessingStatus:
    """Normalizes processing status strings to canonical uppercase format."""
    v = (val or "").strip().upper()
    if v in ["COMPLETED", "FAILED", "SKIPPED", "INCONCLUSIVE", "UNSUPPORTED"]:
        return v  # type: ignore
    return "COMPLETED"


class ImageAuthenticityResult(BaseModel):
    """Forensic authenticity assessment for a single image evidence item."""
    evidence_id: str
    file_hash: str = ""
    filename: str
    modality: str = "image"
    detector_name: str = MODEL_IDENTIFIER
    model_version: str = MODEL_VERSION
    inference_executed: bool = False
    raw_score: Optional[float] = None  # Probability of synthetic/AI content [0.0 - 1.0]
    spatial_max_score: Optional[float] = None
    c2pa_ai_verified: bool = False
    score_interpretation: str = ""
    decision_threshold: float = 0.50
    assessment: CanonicalAssessment = "INCONCLUSIVE"
    preprocessing_info: Dict[str, Any] = Field(default_factory=dict)
    is_screenshot: bool = False
    screenshot_type: Optional[str] = None  # e.g. "chat_screenshot", "document_scan", "photo"
    provenance: Optional[ProvenanceCheckResult] = None
    relevant_limitations: List[str] = Field(default_factory=list)
    processing_status: CanonicalProcessingStatus = "COMPLETED"
    error_details: Optional[str] = None
    inference_time_ms: float = 0.0
    device_used: str = "cpu"
    from_cache: bool = False
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # Backward compatibility properties
    @property
    def sha256(self) -> str:
        return self.file_hash

    @property
    def model_identifier(self) -> str:
        return self.detector_name

    @property
    def limitations(self) -> List[str]:
        return self.relevant_limitations

    @property
    def error_message(self) -> Optional[str]:
        return self.error_details

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.model_dump_json())


def _find_sentry_checkpoint_path() -> Optional[Path]:
    """Locates the cached Sentry ConvNeXt checkpoint on disk."""
    hf_cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    sentry_dirs = list(hf_cache_dir.glob("models--InfImagine--Sentry_image_models/**/epoch_5.pth"))
    if sentry_dirs:
        return sentry_dirs[0]

    local_path = PROJECT_ROOT / "models_cache" / "sentry" / "epoch_5.pth"
    if local_path.exists():
        return local_path

    return None


def _load_sentry_model() -> Optional[torch.nn.Module]:
    """
    Initializes TorchVision ConvNeXt-Small and loads mapped Sentry weights
    with zero external C++ / mmengine dependencies.
    """
    global _LOADED_MODEL, _MODEL_DEVICE
    if _LOADED_MODEL is not None:
        return _LOADED_MODEL

    ckpt_path = _find_sentry_checkpoint_path()
    if not ckpt_path or not ckpt_path.exists():
        logger.warning(f"Sentry checkpoint not found on disk: {ckpt_path}")
        return None

    try:
        from torchvision.models import convnext_small

        # Mock mmengine HistoryBuffer so torch.load unpickler doesn't raise ModuleNotFoundError
        mmengine = types.ModuleType("mmengine")
        logging_mod = types.ModuleType("mmengine.logging")
        history_mod = types.ModuleType("mmengine.logging.history_buffer")

        class HistoryBuffer:
            min, max, mean, current = "min", "max", "mean", "current"
            def __init__(self, *args, **kwargs): pass

        history_mod.HistoryBuffer = HistoryBuffer
        logging_mod.history_buffer = history_mod
        mmengine.logging = logging_mod

        import sys
        sys.modules["mmengine"] = mmengine
        sys.modules["mmengine.logging"] = logging_mod
        sys.modules["mmengine.logging.history_buffer"] = history_mod

        logger.info(f"Loading Sentry ConvNeXt Small from {ckpt_path} on {_MODEL_DEVICE}...")
        try:
            raw_checkpoint = torch.load(str(ckpt_path), map_location=_MODEL_DEVICE, weights_only=False)
        except TypeError:
            raw_checkpoint = torch.load(str(ckpt_path), map_location=_MODEL_DEVICE)

        state_dict = raw_checkpoint.get("state_dict", raw_checkpoint)
        # Sentry ConvNeXt OpenMMLab mapping to TorchVision ConvNeXt-Small
        mapped_dict = {}
        for k, v in state_dict.items():
            if k.startswith("head.fc."):
                mapped_dict["classifier.2." + k[len("head.fc."):]] = v
            elif k == "backbone.norm3.weight":
                mapped_dict["classifier.0.weight"] = v
            elif k == "backbone.norm3.bias":
                mapped_dict["classifier.0.bias"] = v
            elif k.startswith("backbone."):
                body = k[len("backbone."):]
                m_ds = re.match(r"^downsample_layers\.(\d+)\.(.*)", body)
                if m_ds:
                    ds_idx = int(m_ds.group(1))
                    rest = m_ds.group(2)
                    mapped_dict[f"features.{ds_idx * 2}.{rest}"] = v
                else:
                    m_st = re.match(r"^stages\.(\d+)\.(\d+)\.(.*)", body)
                    if m_st:
                        stage_idx = int(m_st.group(1))
                        block_idx = int(m_st.group(2))
                        sub = m_st.group(3)
                        feat_idx = stage_idx * 2 + 1
                        if sub == "gamma":
                            mapped_dict[f"features.{feat_idx}.{block_idx}.layer_scale"] = v.view(-1, 1, 1)
                        elif sub.startswith("depthwise_conv."):
                            mapped_dict[f"features.{feat_idx}.{block_idx}.block.0." + sub[len("depthwise_conv."):]] = v
                        elif sub.startswith("norm."):
                            mapped_dict[f"features.{feat_idx}.{block_idx}.block.2." + sub[len("norm."):]] = v
                        elif sub.startswith("pointwise_conv1."):
                            mapped_dict[f"features.{feat_idx}.{block_idx}.block.3." + sub[len("pointwise_conv1."):]] = v
                        elif sub.startswith("pointwise_conv2."):
                            mapped_dict[f"features.{feat_idx}.{block_idx}.block.5." + sub[len("pointwise_conv2."):]] = v

        model = convnext_small(num_classes=2)
        model.load_state_dict(mapped_dict, strict=True)
        logger.info("Sentry ConvNeXt Small loaded strictly with 100% layer correspondence.")

        model.to(_MODEL_DEVICE)
        model.eval()
        _LOADED_MODEL = model
        return _LOADED_MODEL
    except Exception as exc:
        logger.error(f"Failed to load Sentry ConvNeXt Small: {exc}")
        return None


def _detect_screenshot_characteristics(img: Image.Image, filename: str) -> Tuple[bool, Optional[str]]:
    """Identifies screenshot characteristics from image metadata, aspect ratio, and UI features."""
    w, h = img.size
    aspect = h / max(w, 1)
    fn_lower = filename.lower()

    if any(k in fn_lower for k in ["screenshot", "chat", "whatsapp", "wa_msg", "convo", "msg"]):
        return True, "messaging_interface_screenshot"
    if 1.9 <= aspect <= 2.4:
        return True, "mobile_device_screen_capture"
    if 0.5 <= aspect <= 0.65 and w >= 1200:
        return True, "desktop_window_capture"
    if any(k in fn_lower for k in ["slip", "form", "invoice", "report", "doc"]):
        return False, "document_scan"

    return False, None


def assess_image_authenticity(
    image_path: Union[str, Path],
    evidence_id: str,
    filename: str = "",
    sha256: str = "",
    force_refresh: bool = False,
) -> ImageAuthenticityResult:
    """
    Runs Sentry ConvNeXt-Small synthetic content detection on an image,
    integrates cryptographic provenance inspection, and reports uncertainties.
    """
    path_obj = Path(image_path)
    fname = filename or path_obj.name
    cache_key = f"{sha256}::{MODEL_IDENTIFIER}::{MODEL_VERSION}"

    # 1. Check cache first unless force_refresh is requested
    if not force_refresh and sha256 and IMAGE_AUTH_CACHE_FILE.exists():
        with _CACHE_LOCK:
            try:
                cache_data = json.loads(IMAGE_AUTH_CACHE_FILE.read_text(encoding="utf-8"))
                entry = cache_data.get(cache_key)
                if entry and entry.get("processing_status") in ["COMPLETED", "completed"]:
                    entry["from_cache"] = True
                    entry["inference_executed"] = False
                    # Normalize legacy assessment
                    entry["assessment"] = normalize_assessment(entry.get("assessment", ""))
                    entry["processing_status"] = normalize_processing_status(entry.get("processing_status", ""))
                    if "file_hash" not in entry:
                        entry["file_hash"] = entry.get("sha256", sha256)
                    if "detector_name" not in entry:
                        entry["detector_name"] = entry.get("model_identifier", MODEL_IDENTIFIER)
                    if "relevant_limitations" not in entry:
                        entry["relevant_limitations"] = entry.get("limitations", [])
                    if "error_details" not in entry:
                        entry["error_details"] = entry.get("error_message")
                    return ImageAuthenticityResult(**entry)
            except Exception:
                pass

    # 2. Check file presence
    if not path_obj.exists() or not path_obj.is_file():
        return ImageAuthenticityResult(
            evidence_id=evidence_id,
            filename=fname,
            file_hash=sha256,
            inference_executed=False,
            processing_status="FAILED",
            error_details=f"Image file not found: {path_obj}",
            assessment="INCONCLUSIVE",
            relevant_limitations=["File not accessible on disk."],
        )

    # 3. Provenance Check (C2PA / EXIF / Metadata)
    prov = inspect_media_provenance(
        file_path=path_obj,
        evidence_id=evidence_id,
        filename=fname,
        sha256=sha256,
        file_type="image",
    )

    # 4. Open and validate image
    try:
        pil_img = Image.open(path_obj).convert("RGB")
    except Exception as exc:
        return ImageAuthenticityResult(
            evidence_id=evidence_id,
            filename=fname,
            file_hash=sha256,
            provenance=prov,
            inference_executed=False,
            processing_status="FAILED",
            error_details=f"Image decode error: {exc}",
            assessment="INCONCLUSIVE",
            relevant_limitations=["Cannot decode image file."],
        )

    is_screenshot, screenshot_ctx = _detect_screenshot_characteristics(pil_img, fname)

    # 5. Load model and run inference under lock
    with _IMAGE_DETECTOR_LOCK:
        model = _load_sentry_model()
        if model is None:
            return ImageAuthenticityResult(
                evidence_id=evidence_id,
                filename=fname,
                file_hash=sha256,
                provenance=prov,
                inference_executed=False,
                processing_status="FAILED",
                error_details="Sentry ConvNeXt model weights not available locally.",
                assessment="INCONCLUSIVE",
                is_screenshot=is_screenshot,
                screenshot_type=screenshot_ctx,
                relevant_limitations=["Sentry ConvNeXt model unavailable; assessment marked inconclusive."],
            )

        t0 = time.perf_counter()
        try:
            import torchvision.transforms as T

            # Sentry normalization values: [123.675, 116.28, 103.53] / 255.0
            mean = [123.675 / 255.0, 116.28 / 255.0, 103.53 / 255.0]
            std = [58.395 / 255.0, 57.12 / 255.0, 57.375 / 255.0]

            w, h = pil_img.size
            aspect = h / max(w, 1)

            # 1. Standard reference center crop on short-edge resized 256 image
            transform_center = T.Compose([
                T.Resize(256, interpolation=T.InterpolationMode.BICUBIC),
                T.CenterCrop(224),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ])

            tensor = transform_center(pil_img).unsqueeze(0).to(_MODEL_DEVICE)

            with torch.no_grad():
                logits = model(tensor)
                probs = torch.softmax(logits, dim=1)[0]
                # Sentry OpenMMLab classification head:
                # Class 0: Fake / Synthetic; Class 1: Real
                prob_fake = float(probs[0].item())

            # 2. Multi-window spatial sampling for non-square or screenshot images
            spatial_scores = [prob_fake]
            if aspect >= 1.25 or aspect <= 0.80 or is_screenshot:
                scale = 256.0 / min(w, h)
                new_w, new_h = int(round(w * scale)), int(round(h * scale))
                resized = pil_img.resize((new_w, new_h), Image.BICUBIC)

                norm_transform = T.Compose([
                    T.ToTensor(),
                    T.Normalize(mean=mean, std=std),
                ])

                if new_h >= new_w:
                    # Tall layout (mobile screenshot or vertical document): sample top and bottom
                    x0 = (new_w - 224) // 2
                    for y0 in [0, max(0, new_h - 224)]:
                        patch = resized.crop((x0, y0, x0 + 224, y0 + 224))
                        with torch.no_grad():
                            t_patch = norm_transform(patch).unsqueeze(0).to(_MODEL_DEVICE)
                            p_patch = torch.softmax(model(t_patch), dim=1)[0, 0].item()
                            spatial_scores.append(p_patch)
                else:
                    # Wide layout (desktop capture or landscape): sample left and right
                    y0 = (new_h - 224) // 2
                    for x0 in [0, max(0, new_w - 224)]:
                        patch = resized.crop((x0, y0, x0 + 224, y0 + 224))
                        with torch.no_grad():
                            t_patch = norm_transform(patch).unsqueeze(0).to(_MODEL_DEVICE)
                            p_patch = torch.softmax(model(t_patch), dim=1)[0, 0].item()
                            spatial_scores.append(p_patch)

            spatial_max = max(spatial_scores)
            spatial_mean = sum(spatial_scores) / len(spatial_scores)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # 3. C2PA Cryptographic Provenance Evaluation
            is_c2pa_ai = bool(prov and getattr(prov, "is_ai_declared", False))

            # 4. Multi-Signal Decision Synthesis
            if is_c2pa_ai:
                assessment = "SYNTHETIC_INDICATORS_DETECTED"
                final_score = round(max(prob_fake, spatial_max, 0.9990), 4)
                ai_decls = getattr(prov, "ai_declarations", [])
                decl_str = "; ".join(ai_decls) if ai_decls else "IPTC trainedAlgorithmicMedia"
                interp = (
                    f"Cryptographically verified synthetic origin: C2PA Content Credentials signed by "
                    f"{getattr(prov, 'signature_issuer', 'PKI')} declare AI generation ({decl_str}). "
                    f"Sentry visual score: {prob_fake:.4f} (spatial max: {spatial_max:.4f})."
                )
            elif prob_fake >= 0.70 or (spatial_max >= 0.85 and spatial_mean >= 0.35):
                assessment = "SYNTHETIC_INDICATORS_DETECTED"
                final_score = round(max(prob_fake, spatial_max), 4)
                interp = (
                    f"Strong synthetic/AI visual generation indicators detected in pixel distribution "
                    f"(center score: {prob_fake:.4f}, spatial maximum: {spatial_max:.4f})."
                )
            elif prob_fake <= 0.30 and spatial_max <= 0.30:
                final_score = round(prob_fake, 4)
                if is_screenshot and screenshot_ctx == "document_scan":
                    assessment = "NO_STRONG_SYNTHETIC_INDICATORS"
                    interp = (
                        f"No significant synthetic visual indicators detected in document canvas "
                        f"(center score: {prob_fake:.4f}). Note: Absence of synthetic indicators on document layouts "
                        f"does not establish factual validity."
                    )
                else:
                    assessment = "NO_STRONG_SYNTHETIC_INDICATORS"
                    interp = (
                        f"No significant synthetic generation indicators detected in image pixel distribution "
                        f"(center score: {prob_fake:.4f}, spatial maximum: {spatial_max:.4f})."
                    )
            else:
                assessment = "INCONCLUSIVE"
                final_score = round(prob_fake, 4)
                interp = (
                    f"Borderline synthetic score ({prob_fake:.4f}, spatial max: {spatial_max:.4f}) "
                    f"between decision thresholds [0.30, 0.70]; inconclusive."
                )

            # Taxonomy and limitation notes
            limits = [
                "Sentry ConvNeXt evaluates generative diffusion and GAN artifacts in pixel distributions.",
                "Taxonomy Distinction: Distinguishes synthesized pixel textures (AI-generated photos) from natural camera photos. Cannot independently prove whether a messaging UI capture represents a real conversation.",
                "Absence of synthetic indicators does NOT establish judicial authenticity or absence of tampering.",
            ]
            if is_screenshot:
                limits.append(
                    f"Image exhibits screenshot/UI characteristics ({screenshot_ctx}). "
                    "Detectors evaluate rendering artifacts of the image file, NOT the factual veracity of text depicted inside."
                )
            if screenshot_ctx == "document_scan":
                limits.append(
                    "Document scans with flat text canvases exhibit domain shift from natural scene training sets; "
                    "assessment should be correlated with C2PA metadata and document forensic analysis."
                )
            if is_c2pa_ai:
                limits.append(
                    "C2PA assertions originate from cryptographically signed manifest containers. "
                    "If manifest is altered or removed, detection reverts to neural pixel heuristics."
                )

            prep_info = {
                "input_dimensions": f"{pil_img.width}x{pil_img.height}",
                "channels": "RGB",
                "resize": 256,
                "center_crop": 224,
                "spatial_patches_evaluated": len(spatial_scores),
                "center_score": round(prob_fake, 4),
                "spatial_max": round(spatial_max, 4),
                "spatial_mean": round(spatial_mean, 4),
                "c2pa_ai_verified": is_c2pa_ai,
                "normalization": "Sentry [123.675, 116.28, 103.53]/255",
            }

            res = ImageAuthenticityResult(
                evidence_id=evidence_id,
                filename=fname,
                file_hash=sha256,
                detector_name=MODEL_IDENTIFIER,
                model_version=MODEL_VERSION,
                inference_executed=True,
                raw_score=final_score,
                spatial_max_score=round(spatial_max, 4),
                c2pa_ai_verified=is_c2pa_ai,
                score_interpretation=interp,
                decision_threshold=0.50,
                assessment=assessment,
                preprocessing_info=prep_info,
                is_screenshot=is_screenshot,
                screenshot_type=screenshot_ctx,
                provenance=prov,
                relevant_limitations=limits,
                processing_status="COMPLETED",
                error_details=None,
                inference_time_ms=round(elapsed_ms, 2),
                device_used=_MODEL_DEVICE,
                from_cache=False,
            )

            # Save to disk cache
            if sha256:
                with _CACHE_LOCK:
                    try:
                        IMAGE_AUTH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                        c_dict = {}
                        if IMAGE_AUTH_CACHE_FILE.exists():
                            c_dict = json.loads(IMAGE_AUTH_CACHE_FILE.read_text(encoding="utf-8"))
                        c_dict[cache_key] = res.model_dump()
                        IMAGE_AUTH_CACHE_FILE.write_text(json.dumps(c_dict, indent=2, default=str), encoding="utf-8")
                    except Exception as exc:
                        logger.warning(f"Failed to write image authenticity cache: {exc}")

            return res

        except Exception as exc:
            logger.error(f"Sentry inference error for {fname}: {exc}")
            return ImageAuthenticityResult(
                evidence_id=evidence_id,
                filename=fname,
                file_hash=sha256,
                provenance=prov,
                inference_executed=False,
                processing_status="FAILED",
                error_details=f"Inference exception: {exc}",
                assessment="DETECTION_FAILED",
                is_screenshot=is_screenshot,
                screenshot_type=screenshot_ctx,
                relevant_limitations=["Sentry inference encountered a runtime exception."],
            )
