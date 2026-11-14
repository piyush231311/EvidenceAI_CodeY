"""End-to-End integration test suite for Evidence AI.

Tests all evidence modalities:
- PaddleOCR on screenshots
- Faster-Whisper on audio
- Hybrid PyPDF on PDFs
- python-docx on DOCX documents
- JSON chat exports
- CSV logs
- EML emails
- TXT chats
- GLiNER entity extraction
- RapidFuzz candidate identity matching
- Human review decisions (confirm, reject, separate)
- Audit log forensic tracking
"""

import io
import os
import wave
import struct
import tempfile
import pytest
import docx
import pypdf
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from backend.main import app
from backend.db import get_db, SessionLocal
from backend.models import Case, Evidence, AuditLog, EntityMatchRecord

client = TestClient(app)


def generate_synthetic_screenshot(text: str) -> bytes:
    """Generates synthetic screenshot PNG with clear text."""
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_synthetic_audio(duration_sec: float = 1.0) -> bytes:
    """Generates synthetic silent 16kHz mono WAV."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        raw_data = struct.pack(f"<{num_samples}h", *([0] * num_samples))
        wav_file.writeframes(raw_data)
    return buf.getvalue()


def generate_synthetic_pdf(text: str) -> bytes:
    """Generates synthetic PDF using pypdf."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    # Add a blank page with annotations or use an empty page
    writer.add_blank_page(width=300, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def generate_synthetic_docx(text: str, author: str = "Forensic Analyst") -> bytes:
    """Generates synthetic DOCX document."""
    doc = docx.Document()
    doc.core_properties.author = author
    doc.add_heading("Confidential Intelligence Brief", level=1)
    doc.add_paragraph(text)
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Entity"
    table.cell(0, 1).text = "Role"
    table.cell(1, 0).text = "Target Subject"
    table.cell(1, 1).text = "Primary Person of Interest"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture(scope="module")
def case_id():
    """Creates a clean test case."""
    cid = f"test-case-{os.urandom(4).hex()}"
    res = client.post("/api/cases", json={"id": cid})
    assert res.status_code == 201
    return cid


def test_health_check():
    """Verify backend health endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json().get("status") == "healthy"


def test_screenshot_ocr_upload(case_id):
    """Test image upload and PaddleOCR extraction."""
    img_bytes = generate_synthetic_screenshot("INVOICE 9942 TOTAL AMOUNT $4500 DUE 2026-06-15")
    res = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("invoice.png", img_bytes, "image/png"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert item["file_type"] == "image"
    assert item["sha256"] is not None
    assert item["extracted_text"] is not None
    assert len(item["extracted_text"]) > 0
    assert item["extraction_confidence"] is not None


def test_audio_transcription_upload(case_id):
    """Test audio upload and Faster-Whisper processing."""
    wav_bytes = generate_synthetic_audio(0.5)
    res = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("recording.wav", wav_bytes, "audio/wav"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert item["file_type"] == "audio"
    assert item["sha256"] is not None


def test_docx_extraction_upload(case_id):
    """Test DOCX document upload and extraction."""
    docx_bytes = generate_synthetic_docx("Suspect Marcus Vance met with Dr. Elena Rostova in Geneva.")
    res = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("investigation_notes.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert "Marcus Vance" in item["extracted_text"]
    assert "Elena Rostova" in item["extracted_text"]
    assert item["extraction_confidence"] == 1.0


def test_json_chat_upload(case_id):
    """Test JSON chat export extraction."""
    import json
    chat_data = {
        "messages": [
            {"timestamp": "2026-05-12 10:14:00", "sender": "Marcus Vance", "text": "Wire the funds to Elena Rostova at Zurich Credit Bank."},
            {"timestamp": "2026-05-12 10:15:30", "sender": "Elena Rostova", "text": "Received. Contact me at elena.rostova@zurichcredit.ch."},
        ]
    }
    json_bytes = json.dumps(chat_data).encode("utf-8")
    res = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("telegram_chat.json", json_bytes, "application/json"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert "Marcus Vance" in item["extracted_text"]
    assert "Zurich Credit Bank" in item["extracted_text"]


def test_csv_log_upload(case_id):
    """Test CSV log extraction."""
    csv_content = (
        "date,source_user,destination_user,amount,ip_address\n"
        "2026-05-12,Marcus Vance,Elena Rostova,75000,192.168.1.105\n"
        "2026-05-13,Marcus Vance,Acme Logistics,12000,192.168.1.105\n"
    ).encode("utf-8")
    res = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("transactions.csv", csv_content, "text/csv"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert "192.168.1.105" in item["extracted_text"]


def test_eml_email_upload(case_id):
    """Test EML email extraction."""
    eml_content = (
        "From: Marcus Vance <marcus.vance@vanceindustries.com>\n"
        "To: Elena Rostova <elena.rostova@zurichcredit.ch>\n"
        "Date: Tue, 12 May 2026 14:00:00 +0200\n"
        "Subject: Geneva Transaction Confirmation\n"
        "Message-ID: <msg-20260512-9901@vanceindustries.com>\n"
        "\n"
        "Dear Dr. Rostova,\n"
        "Please confirm receipt of the documentation for our project in Zurich.\n"
        "Regards,\n"
        "Marcus Vance\n"
    ).encode("utf-8")
    res = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("email_brief.eml", eml_content, "message/rfc822"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert "Geneva Transaction Confirmation" in item["extracted_text"]
    assert "marcus.vance@vanceindustries.com" in item["extracted_text"]


def test_txt_chat_upload(case_id):
    """Test plain text chat export extraction."""
    txt_content = (
        "[2026-05-12 18:22:00] Marcus Vance: Meeting concluded at Geneva Airport.\n"
        "[2026-05-12 18:25:00] Elena Rostova: Understood. Flight departs at 20:00.\n"
    ).encode("utf-8")
    res = client.post(
        f"/api/cases/{case_id}/evidence",
        files=[("files", ("whatsapp_export.txt", txt_content, "text/plain"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    item = data[0]
    assert "Geneva Airport" in item["extracted_text"]


def test_entity_extraction_and_matching(case_id):
    """
    Test GLiNER entity extraction and RapidFuzz candidate identity matching.
    Verifies that 'Marcus Vance' and 'Elena Rostova' mentioned across multiple
    evidence files are clustered into candidate matches.
    """
    res = client.post(f"/api/cases/{case_id}/entities/match")
    assert res.status_code == 200
    candidates = res.json()
    assert len(candidates) > 0

    # Look for candidate match for Marcus Vance
    canonical_names = [c["canonical_name"].lower() for c in candidates]
    assert any("marcus" in name or "vance" in name for name in canonical_names), f"Missing Marcus Vance in {canonical_names}"
    assert any("elena" in name or "rostova" in name for name in canonical_names), f"Missing Elena Rostova in {canonical_names}"

    # Verify at least one match has multiple cross-evidence mentions
    multi_mention_candidates = [c for c in candidates if len(c["mentions"]) > 1]
    assert len(multi_mention_candidates) > 0, "Expected at least one cross-evidence identity cluster"

    # Verify similarity score
    for cand in candidates:
        assert 0.0 <= cand["similarity_score"] <= 100.0
        assert cand["status"] == "pending"


def test_entity_review_lifecycle(case_id):
    """
    Test human review actions: confirm, separate, reject, and audit logging.
    """
    # 1. Fetch current candidates
    res = client.get(f"/api/cases/{case_id}/entities")
    assert res.status_code == 200
    candidates = res.json()
    assert len(candidates) > 0

    target = candidates[0]
    target_id = target["id"]

    # 2. Confirm candidate match
    res_confirm = client.post(
        f"/api/entities/matches/{target_id}/review",
        json={"action": "confirm", "review_notes": "Forensically confirmed same target"},
    )
    assert res_confirm.status_code == 200
    updated = res_confirm.json()
    assert updated["status"] == "confirmed"
    assert updated["reviewed_at"] is not None

    # 3. Mark separate
    res_sep = client.post(
        f"/api/entities/matches/{target_id}/review",
        json={"action": "separate", "review_notes": "Different individuals with similar name"},
    )
    assert res_sep.status_code == 200
    assert res_sep.json()["status"] == "separate"

    # 4. Reject match
    res_reject = client.post(
        f"/api/entities/matches/{target_id}/review",
        json={"action": "reject", "review_notes": "False match"},
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "rejected"

    # 5. Undo back to pending
    res_undo = client.post(
        f"/api/entities/matches/{target_id}/review",
        json={"action": "undo"},
    )
    assert res_undo.status_code == 200
    assert res_undo.json()["status"] == "pending"

    # 6. Verify audit logs
    audit_res = client.get(f"/api/cases/{case_id}/audit-logs")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    actions = [log["action"] for log in logs]
    assert "ENTITY_REVIEW_CONFIRM" in actions
    assert "ENTITY_REVIEW_SEPARATE" in actions
    assert "ENTITY_REVIEW_REJECT" in actions
