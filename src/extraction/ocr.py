"""OCR extraction module using pretrained PaddleOCR for Evidence AI."""

import os
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
_OCR_DEVICE = None

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def get_ocr_engine(device: str = "cpu"):
    """
    Get or initialize the PaddleOCR engine instance.

    Args:
        device: Device to use for inference ('cpu' or 'gpu').

    Returns:
        PaddleOCR engine instance.
    """
    global _OCR_ENGINE, _OCR_DEVICE

    if _OCR_ENGINE is None or _OCR_DEVICE != device:
        from paddleocr import PaddleOCR

        # enable_mkldnn=False ensures reliable CPU static runner execution on Windows
        _OCR_ENGINE = PaddleOCR(
            device=device,
            enable_mkldnn=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        _OCR_DEVICE = device

    return _OCR_ENGINE


def extract_text_from_image(
    image_path: Union[str, Path],
    device: str = "cpu",
) -> Dict[str, Any]:
    """
    Extract recognized text and confidence scores from an image or screenshot.

    Args:
        image_path: Path to PNG, JPG, or JPEG image file.
        device: 'cpu' for CPU inference (default) or 'gpu' for GPU acceleration.

    Returns:
        Dict containing:
            - 'text': Full concatenated extracted text.
            - 'confidence': Average confidence score (0.0 to 1.0).
            - 'lines': List of dicts, each with:
                - 'text': Recognized line string.
                - 'confidence': Recognition confidence score.
                - 'box': Bounding box coordinates.
            - 'success': Boolean indicating extraction success.

    Raises:
        FileNotFoundError: If image file does not exist.
        ValueError: If file format is not supported (only PNG, JPG, JPEG).
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

    engine = get_ocr_engine(device=device)

    # Run inference using predict
    predictions = engine.predict(str(image_path))

    extracted_lines: List[Dict[str, Any]] = []
    total_score = 0.0

    for result in predictions:
        # PaddleOCR 3.x returns dict-like results with rec_texts, rec_scores, rec_boxes
        rec_texts = result.get("rec_texts", []) if hasattr(result, "get") else []
        rec_scores = result.get("rec_scores", []) if hasattr(result, "get") else []
        rec_boxes = result.get("rec_boxes", []) if hasattr(result, "get") else []

        # Convert rec_boxes from numpy arrays to lists if necessary
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
        "success": True,
    }
