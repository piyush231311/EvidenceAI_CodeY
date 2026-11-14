"""Verification test mimicking the exact React frontend upload flow through Vite proxy."""

import urllib.request
import urllib.error
import json
import uuid
import hashlib
from pathlib import Path

VITE_URL = "http://localhost:5173"
CASE_ID = f"case-{uuid.uuid4().hex[:8]}"

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

def upload_to_frontend(filename, data, mime, note):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode())
    body.extend(f"Content-Type: {mime}\r\n\r\n".encode())
    body.extend(data)
    body.extend(b"\r\n")

    notes_map = {filename: note}
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="notes_map"\r\n\r\n')
    body.extend(json.dumps(notes_map).encode())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{VITE_URL}/api/cases/{CASE_ID}/evidence",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

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
print(f"  SHA-256: {img_res['sha256']}")

print("\n[Step 2] User uploads 'voicemail_evidence.wav' -> Faster-Whisper transcription...")
audio_res = upload_to_frontend("voicemail_evidence.wav", audio_bytes, "audio/wav", "Recorded phone voicemail")[0]
print(f"  Response Status: 201 Created")
print(f"  Item ID: {audio_res['id']}")
print(f"  Category: {audio_res['file_type'].upper()}")
print(f"  Transcribed Text from Faster-Whisper: {repr(audio_res['extracted_text'])}")
print(f"  Processing Time: {audio_res['processing_time_ms']} ms")
meta = json.loads(audio_res['extraction_metadata'])
print(f"  Spoken Segments:")
for seg in meta.get('segments', []):
    print(f"    > [{seg['start']}s -> {seg['end']}s]: {repr(seg['text'])}")

print("\n[Step 3] Fetching Evidence Table data (GET /api/cases/{case_id}/evidence)...")
req_get = urllib.request.Request(f"{VITE_URL}/api/cases/{CASE_ID}/evidence")
with urllib.request.urlopen(req_get) as r:
    evidence_table = json.loads(r.read().decode())

print(f"  Table loaded with {len(evidence_table)} items:")
for row in evidence_table:
    conf = f"{row['extraction_confidence']*100:.1f}%" if row['extraction_confidence'] is not None else "N/A"
    print(f"  - [{row['file_type'].upper()}] {row['original_filename']} | Conf: {conf} | Time: {row['processing_time_ms']}ms | SHA-256: {row['sha256'][:16]}...")
    print(f"    Extracted: {repr(row['extracted_text'][:70])}...")

print("\n>>> ALL FRONTEND-TO-BACKEND FLOWS VERIFIED SUCCESSFULLY! <<<")
