"""Evidence Extraction Modules - OCR and Audio Transcription"""

from .ocr import extract_text_from_image
from .transcription import transcribe_audio

__all__ = ["extract_text_from_image", "transcribe_audio"]
