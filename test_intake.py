import os
import sys
import json
import uuid
import hashlib
import sqlite3
import urllib.request
import urllib.error

CASE_ID = str(uuid.uuid4())
BASE_URL = "http://127.0.0.1:8000"

print(f"=== EVIDENCE AI INTAKE MVP TEST ===")
print(f"Testing with Case ID: {CASE_ID}")

# 1. Create sample test files
os.makedirs("test_files", exist_ok=True)

# Minimal 1x1 transparent PNG bytes
png_bytes = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89,
    0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41, 0x54,  # IDAT
    0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4,
    0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,  # IEND
    0xAE, 0x42, 0x60, 0x82
])
image_path = "test_files/harassment_screenshot.png"
with open(image_path, "wb") as f:
    f.write(png_bytes)

# Minimal MP3 frame header + bytes
audio_bytes = b"\xFF\xFB\x90\x64" + b"\x00" * 300
audio_path = "test_files/threatening_voicemail.mp3"
with open(audio_path, "wb") as f:
    f.write(audio_bytes)

# Chat export text
text_content = """[2026-11-12 21:04:12] Sender: If you speak to the authorities, you will regret it.
[2026-11-12 21:05:03] Victim: Please stop contacting me. I am archiving these messages.
[2026-11-12 21:06:22] Sender: You can't hide anything.
"""
text_bytes = text_content.encode("utf-8")
text_path = "test_files/whatsapp_chat_export.txt"
with open(text_path, "wb") as f:
    f.write(text_bytes)

print("\n[Step 1] Created sample files:")
print(f"  - Image: {image_path} ({len(png_bytes)} bytes, SHA-256: {hashlib.sha256(png_bytes).hexdigest()})")
print(f"  - Audio: {audio_path} ({len(audio_bytes)} bytes, SHA-256: {hashlib.sha256(audio_bytes).hexdigest()})")
print(f"  - Text:  {text_path} ({len(text_bytes)} bytes, SHA-256: {hashlib.sha256(text_bytes).hexdigest()})")

# 2. Upload files via multipart request
boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
body = bytearray()

files_to_upload = [
    ("harassment_screenshot.png", png_bytes, "image/png", "WhatsApp screenshot of threatening message"),
    ("threatening_voicemail.mp3", audio_bytes, "audio/mpeg", "Voicemail recording left on 12 Nov"),
    ("whatsapp_chat_export.txt", text_bytes, "text/plain", "Exported chat history with timestamp logs")
]

notes_map = {}
for filename, content, mime, note in files_to_upload:
    notes_map[filename] = note
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    body.extend(content)
    body.extend(b"\r\n")

# Add notes_map field
body.extend(f"--{boundary}\r\n".encode("utf-8"))
body.extend(b'Content-Disposition: form-data; name="notes_map"\r\n\r\n')
body.extend(json.dumps(notes_map).encode("utf-8"))
body.extend(b"\r\n")

body.extend(f"--{boundary}--\r\n".encode("utf-8"))

upload_url = f"{BASE_URL}/api/cases/{CASE_ID}/evidence"
req = urllib.request.Request(
    upload_url,
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST"
)

print(f"\n[Step 2] Sending POST to {upload_url}...")
try:
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        upload_resp = json.loads(resp.read().decode("utf-8"))
        print(f"  HTTP {status_code} Created - Response contains {len(upload_resp)} item(s)")
except urllib.error.HTTPError as e:
    print(f"  Upload failed HTTP {e.code}: {e.read().decode('utf-8')}")
    sys.exit(1)

# 3. Query GET /api/cases/{case_id}/evidence
get_url = f"{BASE_URL}/api/cases/{CASE_ID}/evidence"
print(f"\n[Step 3] Querying GET {get_url}...")
with urllib.request.urlopen(get_url) as resp:
    evidence_items = json.loads(resp.read().decode("utf-8"))
    print(f"  Retrieved {len(evidence_items)} evidence records for case {CASE_ID}:")
    for item in evidence_items:
        print(f"    - ID: {item['id']}")
        print(f"      Filename: {item['original_filename']}")
        print(f"      Category: {item['file_type']} | MIME: {item['mime_type']}")
        print(f"      Size: {item['size_bytes']} bytes")
        print(f"      SHA-256: {item['sha256']}")
        print(f"      Authenticity Gate: passed={item['authenticity_passed']}, score={item['authenticity_score']}")
        print(f"      Notes: {item['notes']}")
        print(f"      Stored Path: {item['stored_path']}")

# 4. Stream back each file and verify byte integrity
print(f"\n[Step 4] Verifying File Streaming (GET /api/evidence/{{id}}/file)...")
for item in evidence_items:
    file_url = f"{BASE_URL}/api/evidence/{item['id']}/file"
    with urllib.request.urlopen(file_url) as resp:
        downloaded_bytes = resp.read()
        downloaded_hash = hashlib.sha256(downloaded_bytes).hexdigest()
        assert downloaded_hash == item['sha256'], f"Hash mismatch for {item['original_filename']}!"
        print(f"  ✓ Streamed {item['original_filename']}: {len(downloaded_bytes)} bytes, SHA-256 verified match!")

# 5. Verify direct database records
print(f"\n[Step 5] Direct SQLite Database Inspection (evidence_ai.db)...")
conn = sqlite3.connect("evidence_ai.db")
cursor = conn.cursor()

# Check Cases table
cursor.execute("SELECT id, created_at FROM cases WHERE id = ?", (CASE_ID,))
case_row = cursor.fetchone()
print(f"  [cases table] Found case: id={case_row[0]}, created_at={case_row[1]}")

# Check Evidence table
cursor.execute("SELECT id, original_filename, file_type, size_bytes, sha256, authenticity_passed FROM evidence WHERE case_id = ?", (CASE_ID,))
evidence_rows = cursor.fetchall()
print(f"  [evidence table] Found {len(evidence_rows)} rows:")
for row in evidence_rows:
    print(f"    - {row[1]} ({row[2]}): {row[3]} bytes, sha256={row[4][:12]}..., auth_passed={row[5]}")

# Check Audit Log table
cursor.execute("SELECT id, action, evidence_id, timestamp, details FROM audit_log WHERE case_id = ? ORDER BY timestamp ASC", (CASE_ID,))
audit_rows = cursor.fetchall()
print(f"  [audit_log table] Found {len(audit_rows)} append-only forensic audit entries:")
for row in audit_rows:
    details = json.loads(row[4])
    print(f"    - Action: {row[1]} | Evidence: {row[2]} | Time: {row[3]}")
    print(f"      Details: file={details.get('original_filename')} | sha256={details.get('sha256')[:12]}...")

conn.close()

# 6. Verify filesystem storage untouched
print(f"\n[Step 6] Verifying storage/originals/{CASE_ID}/ files on disk...")
storage_folder = os.path.join("storage", "originals", CASE_ID)
stored_files = os.listdir(storage_folder)
print(f"  Files in {storage_folder}: {stored_files}")
assert len(stored_files) == 3, "Expected 3 files stored on disk!"

print("\n✅ ALL INTAKE INTEGRITY CHECKS PASSED SUCCESSFULLY!")
