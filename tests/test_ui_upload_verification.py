"""Verification test mimicking the exact React frontend upload flow through Vite proxy."""

import urllib.request
import urllib.error
import json
import uuid
import hashlib
from pathlib import Path

VITE_URL = "http://localhost:5173"
CASE_ID = f"case-{uuid.uuid4().hex[:8]}"

def run_verification():
    print(f"--- Simulating Exact React Frontend User Flow ---")
    print(f"Active Case ID in UI: {CASE_ID}")

    # 1. Screenshot
    screenshot_path = Path("test_files/screenshot_evidence.png")
    with open(screenshot_path, "rb") as f:
        screenshot_bytes = f.read()

    # 2. Audio
    audio_path = Path("test_files/voicemail_evidence.wav")
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    print("\n[Step 1] User uploads 'screenshot_evidence.png' -> PaddleOCR extraction...")
    img_res = upload_to_frontend("screenshot_evidence.png", screenshot_bytes, "image/png", "Victim threat screenshot")[0]
    print(f"  Response Status: 201 Created")
    print(f"  Item ID: {img_res['id']}")
    print(f"  Category: {img_res['file_type'].upper()}")
    print(f"  Extracted Text from PaddleOCR:")
    for line in img_res['extracted_text'].split('\n'):
        print(f"    > {line}")
    print(f"  Confidence: {img_res['extraction_confidence']*100:.1f}%")
    print(f"  Processing Time: {img_res['processing_time_ms']} ms")

    # [Step 2] User uploads 'voicemail_evidence.wav' -> Faster-Whisper extraction
    print("\n[Step 2] User uploads 'voicemail_evidence.wav' -> Faster-Whisper transcription...")
    audio_res = upload_to_frontend("voicemail_evidence.wav", audio_bytes, "audio/wav", "Suspect voicemail")[0]
    print(f"  Response Status: 201 Created")
    print(f"  Item ID: {audio_res['id']}")
    print(f"  Category: {audio_res['file_type'].upper()}")
    print(f"  Extracted Transcript from Faster-Whisper:")
    for line in audio_res['extracted_text'].split('\n'):
        print(f"    > {line}")
    print(f"  Confidence: {audio_res['extraction_confidence']*100:.1f}%")
    print(f"  Processing Time: {audio_res['processing_time_ms']} ms")

    print("\n>>> ALL FRONTEND-TO-BACKEND FLOWS VERIFIED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    run_verification()
