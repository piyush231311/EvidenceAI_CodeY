"""OCR extraction module using optimized pretrained PaddleOCR for Evidence AI."""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Configure Paddle cache directories within project workspace
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODELS_CACHE = PROJECT_ROOT / "models_cache"
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(DEFAULT_MODELS_CACHE / "paddlex"))
os.environ.setdefault("PADDLE_HOME", str(DEFAULT_MODELS_CACHE / "paddle"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Global singleton to avoid re-initializing models repeatedly
_OCR_ENGINE = None
_OCR_CONFIG = None

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def get_ocr_engine(
    device: str = "cpu",
    det_model: str = "PP-OCRv6_small_det",
    rec_model: str = "PP-OCRv6_small_rec",
):
    """
    Get or initialize the PaddleOCR engine instance with lazy loading and singleton caching.

    Args:
        device: Device to use for inference ('cpu' or 'gpu').
        det_model: Detection model name (default: PP-OCRv6_small_det for 4x speedup).
        rec_model: Recognition model name (default: PP-OCRv6_small_rec).

    Returns:
        PaddleOCR engine instance.
    """
    global _OCR_ENGINE, _OCR_CONFIG

    current_config = (device, det_model, rec_model)

    if _OCR_ENGINE is None or _OCR_CONFIG != current_config:
        from paddleocr import PaddleOCR

        # enable_mkldnn=False ensures reliable CPU static runner execution on Windows
        # disabling unused doc unwarping / orientation classifies saves 60% load time
        _OCR_ENGINE = PaddleOCR(
            text_detection_model_name=det_model,
            text_recognition_model_name=rec_model,
            device=device,
            enable_mkldnn=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        _OCR_CONFIG = current_config

    return _OCR_ENGINE


def extract_text_from_image(
    image_path: Union[str, Path],
    device: str = "cpu",
    det_model: str = "PP-OCRv6_small_det",
    rec_model: str = "PP-OCRv6_small_rec",
) -> Dict[str, Any]:
    """
    Extract recognized text and confidence scores from an image or screenshot.

    Args:
        image_path: Path to PNG, JPG, JPEG, or WEBP image file.
        device: 'cpu' for CPU inference (default) or 'gpu' for GPU acceleration.
        det_model: OCR detection model.
        rec_model: OCR recognition model.

    Returns:
        Dict containing:
            - 'text': Full concatenated extracted text.
            - 'confidence': Average confidence score (0.0 to 1.0).
            - 'lines': List of dicts with 'text', 'confidence', 'box'.
            - 'processing_time_ms': Inference time in milliseconds.
            - 'success': Boolean indicating extraction success.

    Raises:
        FileNotFoundError: If image file does not exist.
        ValueError: If file format is not supported.
    """
    image_path = Path(image_path).resolve()

    if not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    ext = image_path.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension '{ext}'. "
            f"Supported extensions are: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    t_start = time.perf_counter()
    engine = get_ocr_engine(device=device, det_model=det_model, rec_model=rec_model)

    # Run inference
    predictions = engine.predict(str(image_path))
    inf_time_ms = round((time.perf_counter() - t_start) * 1000, 2)

    extracted_lines: List[Dict[str, Any]] = []
    total_score = 0.0

    for result in predictions:
        rec_texts = result.get("rec_texts", []) if hasattr(result, "get") else []
        rec_scores = result.get("rec_scores", []) if hasattr(result, "get") else []
        rec_boxes = result.get("rec_boxes", []) if hasattr(result, "get") else []

        for idx, text in enumerate(rec_texts):
            score = float(rec_scores[idx]) if idx < len(rec_scores) else 0.0
            box = rec_boxes[idx].tolist() if idx < len(rec_boxes) and hasattr(rec_boxes[idx], "tolist") else None

            extracted_lines.append({
                "text": text,
                "confidence": round(score, 4),
                "box": box,
            })
            total_score += score

    count = len(extracted_lines)
    avg_confidence = round(total_score / count, 4) if count > 0 else 0.0
    full_text = "\n".join(item["text"] for item in extracted_lines)

    return {
        "text": full_text,
        "confidence": avg_confidence,
        "lines": extracted_lines,
        "processing_time_ms": inf_time_ms,
        "success": True,
    }
