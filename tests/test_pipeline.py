"""Verification tests for PaddleOCR and Faster-Whisper in Evidence AI."""

import os
import sys
import tempfile
import math
import struct
import wave
from pathlib import Path
from PIL import Image, ImageDraw

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Order: ctranslate2 must be imported before paddle on Windows
import ctranslate2
from src.extraction.ocr import extract_text_from_image
from src.extraction.transcription import transcribe_audio


def test_paddleocr_inference():
    print("\n--- Testing PaddleOCR Extraction ---")
    # Generate a synthetic PNG test image with text
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_png = tmp.name

    try:
        img = Image.new("RGB", (450, 120), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((25, 45), "CONFIDENTIAL EVIDENCE 2026", fill=(0, 0, 0))
        img.save(tmp_png)

        result = extract_text_from_image(tmp_png)
        print(f"Extracted text: {repr(result['text'])}")
        print(f"Confidence score: {result['confidence']:.4f}")
        print(f"Lines count: {len(result['lines'])}")

        assert result["success"] is True, "Extraction failed"
        assert len(result["lines"]) > 0, "No lines detected"
        assert result["confidence"] > 0.8, f"Low confidence: {result['confidence']}"
        assert "EVIDENCE" in result["text"].upper(), f"Expected 'EVIDENCE' in {result['text']}"
        print("[PASS] PaddleOCR extraction test passed successfully!")
    finally:
        if os.path.exists(tmp_png):
            os.remove(tmp_png)


def test_faster_whisper_inference():
    print("\n--- Testing Faster-Whisper Transcription ---")
    # Generate a 2.5-second sine wave WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name

    try:
        sample_rate = 16000
        duration = 2.0
        num_samples = int(sample_rate * duration)
        with wave.open(tmp_wav, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(num_samples):
                val = int(32767.0 * 0.1 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
                wf.writeframes(struct.pack("<h", val))

        result = transcribe_audio(tmp_wav)
        print(f"Detected language: {result['language']} (confidence: {result['language_probability']:.4f})")
        print(f"Audio duration: {result['duration']}s")
        print(f"Segments count: {len(result['segments'])}")
        for seg in result["segments"]:
            print(f"  [{seg['start']}s -> {seg['end']}s]: {repr(seg['text'])}")

        assert result["success"] is True, "Transcription failed"
        assert result["duration"] > 0, "Zero duration"
        print("[PASS] Faster-Whisper transcription test passed successfully!")
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)


if __name__ == "__main__":
    test_paddleocr_inference()
    test_faster_whisper_inference()
    print("\n>>> ALL INFERENCE TESTS PASSED SUCCESSFULLY! <<<")
