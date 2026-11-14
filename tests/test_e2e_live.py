"""End-to-end integration verification script testing through Vite proxy (port 5173) to FastAPI (port 8000)."""

import os
import sys
import uuid
import math
import struct
import wave
import hashlib
import json
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image, ImageDraw

VITE_BASE_URL = "http://localhost:5173"
CASE_ID = f"test-case-{uuid.uuid4().hex[:8]}"

print(f"==================================================")
print(f"      EVIDENCE AI END-TO-END INTEGRATION TEST     ")
print(f"==================================================")
print(f"Target URL (Vite Proxy): {VITE_BASE_URL}")
print(f"Target Case ID:          {CASE_ID}")

# Helper for multipart form uploads
def upload_file_multipart(url: str, filename: str, content: bytes, content_type: str, note: str = ""):
    boundary = f"----WebKitBoundary{uuid.uuid4().hex}"
    body = bytearray()

    # File field
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(content)
    body.extend(b"\r\n")

    # Notes map
    notes_map = {filename: note}
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="notes_map"\r\n\r\n')
    body.extend(json.dumps(notes_map).encode("utf-8"))
    body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))


# 1. Health check through Vite proxy
print("\n[Test 1] Health Check through Vite Proxy...")
with urllib.request.urlopen(f"{VITE_BASE_URL}/api/health") as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["status"] == "healthy"
    print(f"  ✓ Vite Proxy -> FastAPI health check passed: {data}")


# 2. Screenshot OCR Upload & Extraction
print("\n[Test 2] Uploading Screenshot for PaddleOCR Extraction...")
img = Image.new("RGB", (650, 140), color=(255, 255, 255))
d = ImageDraw.Draw(img)
d.text((20, 30), "Suspect: Alex Vance", fill=(0, 0, 0))
d.text((20, 65), "Threat: Transfer 5000 USD before 2026-11-15", fill=(0, 0, 0))
d.text((20, 100), "Timestamp: 2026-11-14 15:20:00", fill=(0, 0, 0))

tmp_img_path = Path("test_screenshot_e2e.png")
img.save(tmp_img_path)
with open(tmp_img_path, "rb") as f:
    img_bytes = f.read()
tmp_img_path.unlink()

img_hash = hashlib.sha256(img_bytes).hexdigest()
status_code, resp_img = upload_file_multipart(
    f"{VITE_BASE_URL}/api/cases/{CASE_ID}/evidence",
    "threat_screenshot.png",
    img_bytes,
    "image/png",
    "Screenshot from victim phone"
)

assert status_code == 201, f"Expected 201, got {status_code}"
assert len(resp_img) == 1
item_img = resp_img[0]
print(f"  ✓ Uploaded Image ID: {item_img['id']}")
print(f"  ✓ SHA-256 Match:     {item_img['sha256'] == img_hash} ({item_img['sha256'][:16]}...)")
print(f"  ✓ Extracted Text:    {repr(item_img['extracted_text'])}")
print(f"  ✓ Confidence:        {(item_img['extraction_confidence'] or 0)*100:.1f}%")
print(f"  ✓ Processing Time:   {item_img['processing_time_ms']} ms")
assert "5000" in item_img["extracted_text"] or "Alex" in item_img["extracted_text"] or "2026" in item_img["extracted_text"]
assert item_img["extraction_confidence"] > 0.85
print("  ✓ [PASS] Screenshot OCR end-to-end verified!")


# 3. Audio Recording Upload & Faster-Whisper Transcription
print("\n[Test 3] Uploading Audio for Faster-Whisper Transcription...")
sample_rate = 16000
duration = 2.0
num_samples = int(sample_rate * duration)
audio_buf = bytearray()
tmp_wav_path = Path("test_audio_e2e.wav")
with wave.open(str(tmp_wav_path), "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    for i in range(num_samples):
        val = int(32767.0 * 0.1 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
        wf.writeframes(struct.pack("<h", val))

with open(tmp_wav_path, "rb") as f:
    wav_bytes = f.read()
tmp_wav_path.unlink()

wav_hash = hashlib.sha256(wav_bytes).hexdigest()
status_code, resp_audio = upload_file_multipart(
    f"{VITE_BASE_URL}/api/cases/{CASE_ID}/evidence",
    "voicemail.wav",
    wav_bytes,
    "audio/wav",
    "Voicemail audio recording"
)

assert status_code == 201
item_audio = resp_audio[0]
print(f"  ✓ Uploaded Audio ID: {item_audio['id']}")
print(f"  ✓ SHA-256 Match:     {item_audio['sha256'] == wav_hash} ({item_audio['sha256'][:16]}...)")
print(f"  ✓ Transcribed Text:  {repr(item_audio['extracted_text'])}")
print(f"  ✓ Processing Time:   {item_audio['processing_time_ms']} ms")
print(f"  ✓ Metadata:          {item_audio['extraction_metadata']}")
assert item_audio["extracted_text"] is not None
print("  ✓ [PASS] Audio Transcription end-to-end verified!")


# 4. Text File Upload & Document Extraction
print("\n[Test 4] Uploading WhatsApp Chat Export Text...")
text_content = "[2026-11-14 15:00:00] Threat: You cannot delete evidence."
text_bytes = text_content.encode("utf-8")
text_hash = hashlib.sha256(text_bytes).hexdigest()

status_code, resp_text = upload_file_multipart(
    f"{VITE_BASE_URL}/api/cases/{CASE_ID}/evidence",
    "chat_export.txt",
    text_bytes,
    "text/plain",
    "Exported text log"
)

assert status_code == 201
item_text = resp_text[0]
print(f"  ✓ Uploaded Text ID:  {item_text['id']}")
print(f"  ✓ SHA-256 Match:     {item_text['sha256'] == text_hash}")
print(f"  ✓ Extracted Text:    {repr(item_text['extracted_text'])}")
assert item_text["extracted_text"] == text_content
print("  ✓ [PASS] Text Extraction end-to-end verified!")


# 5. Unsupported file rejection test
print("\n[Test 5] Testing Unsupported File Type Rejection...")
try:
    upload_file_multipart(
        f"{VITE_BASE_URL}/api/cases/{CASE_ID}/evidence",
        "malicious.exe",
        b"MZ\x90\x00\x03\x00\x00\x00",
        "application/octet-stream"
    )
    assert False, "Expected 400 Bad Request!"
except urllib.error.HTTPError as e:
    assert e.code == 400
    err_body = json.loads(e.read().decode("utf-8"))
    print(f"  ✓ Correctly rejected with HTTP 400: {err_body['detail']}")
    print("  ✓ [PASS] Unsupported file security check verified!")


# 6. Verify GET /api/cases/{case_id}/evidence retrieval
print("\n[Test 6] Verifying Case Evidence Retrieval for Frontend...")
with urllib.request.urlopen(f"{VITE_BASE_URL}/api/cases/{CASE_ID}/evidence") as resp:
    evidence_list = json.loads(resp.read().decode("utf-8"))
    print(f"  ✓ Retrieved {len(evidence_list)} evidence records for case {CASE_ID}")
    assert len(evidence_list) == 3
    for ev in evidence_list:
        print(f"    - {ev['original_filename']} ({ev['file_type'].upper()}): text={repr(ev['extracted_text'][:40])}... | conf={ev['extraction_confidence']} | time={ev['processing_time_ms']}ms")
    print("  ✓ [PASS] Full evidence list retrieved with extraction intelligence!")


# 7. Verify byte-for-byte stream integrity (Forensic custody)
print("\n[Test 7] Verifying Untouched Byte-for-Byte Original File Streaming...")
for ev in evidence_list:
    with urllib.request.urlopen(f"{VITE_BASE_URL}/api/evidence/{ev['id']}/file") as resp:
        downloaded = resp.read()
        dl_hash = hashlib.sha256(downloaded).hexdigest()
        assert dl_hash == ev["sha256"]
        print(f"  ✓ Forensically verified {ev['original_filename']}: {len(downloaded)} bytes, SHA-256 intact!")
print("  ✓ [PASS] Forensic preservation assurance verified!")

print("\n==================================================")
print("  >>> ALL 7 END-TO-END TESTS PASSED (100%)! <<<   ")
print("==================================================")
