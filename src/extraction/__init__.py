"""Evidence Extraction Modules - OCR, Audio Transcription, and Document Extraction"""

from .ocr import extract_text_from_image
from .transcription import transcribe_audio
from .text_extractor import extract_text_from_document

__all__ = ["extract_text_from_image", "transcribe_audio", "extract_text_from_document"]
