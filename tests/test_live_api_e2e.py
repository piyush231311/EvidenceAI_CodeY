"""Live HTTP End-to-End integration test suite for Evidence AI.

Communicates with the live running FastAPI backend on http://127.0.0.1:8000
exactly as the React frontend does.
"""

import io
import os
import sys
import wave
import struct
import json
import urllib.request
import urllib.parse
import docx
from PIL import Image, ImageDraw

API_BASE = "http://127.0.0.1:8000/api"


def post_multipart(url: str, fields: dict, files: list):
    """Sends a multipart/form-data POST request using standard urllib."""
    boundary = "----EvidenceAIBoundary" + os.urandom(8).hex()
    body = bytearray()

    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(v).encode("utf-8"))
        body.extend(b"\r\n")

    for field_name, filename, data, content_type in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(data)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def run_all_tests():
    print("=== EVIDENCE AI LIVE E2E INTEGRATION TEST SUITE ===")

    # 1. Health check
    print("\n[1/8] Checking backend health...")
    health = get_json(f"{API_BASE}/health")
    assert health.get("status") == "healthy", f"Health failed: {health}"
    print("  -> Backend healthy!")

    # 2. Create case
    case_id = f"CASE-LIVE-{os.urandom(3).hex().upper()}"
    print(f"\n[2/8] Creating Case: {case_id}...")
    case = post_json(f"{API_BASE}/cases", {"id": case_id})
    assert case["id"] == case_id
    print("  -> Case created successfully!")

    # 3. Create synthetic files
    print("\n[3/8] Generating synthetic multi-modal evidence files...")

    # PNG screenshot
    img = Image.new("RGB", (650, 160), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((25, 40), "OFFICIAL INVOICE #9942 TOTAL AMOUNT $45,000", fill=(0, 0, 0))
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG")
    png_bytes = png_buf.getvalue()

    # WAV audio
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<8000h", *([0] * 8000)))
    wav_bytes = wav_buf.getvalue()

    # DOCX
    doc = docx.Document()
    doc.add_heading("Confidential Briefing", level=1)
    doc.add_paragraph("Target suspect Marcus Vance met with Dr. Elena Rostova in Geneva regarding offshore transaction.")
    docx_buf = io.BytesIO()
    doc.save(docx_buf)
    docx_bytes = docx_buf.getvalue()

    # JSON chat
    chat_json = json.dumps({
        "messages": [
            {"timestamp": "2026-05-12 10:14:00", "sender": "Marcus Vance", "text": "Wire the funds to Elena Rostova at Zurich Credit Bank."},
            {"timestamp": "2026-05-12 10:15:30", "sender": "Elena Rostova", "text": "Confirmed. Reach me at elena.rostova@zurichcredit.ch."},
        ]
    }).encode("utf-8")

    # CSV log
    csv_bytes = (
        "date,sender,receiver,amount,ip_address\n"
        "2026-05-12,Marcus Vance,Elena Rostova,45000,192.168.1.105\n"
    ).encode("utf-8")

    # EML email
    eml_bytes = (
        "From: Marcus Vance <marcus.vance@vanceindustries.com>\n"
        "To: Elena Rostova <elena.rostova@zurichcredit.ch>\n"
        "Date: Tue, 12 May 2026 14:00:00 +0200\n"
        "Subject: Geneva Transaction Wire\n"
        "\n"
        "Dear Elena,\nPlease finalize the project files for our Geneva operations.\nRegards,\nMarcus Vance\n"
    ).encode("utf-8")

    # TXT chat log
    txt_bytes = (
        "[2026-05-12 18:22:00] Marcus Vance: Meeting concluded at Geneva Airport.\n"
        "[2026-05-12 18:25:00] Elena Rostova: Flight departs soon.\n"
    ).encode("utf-8")

    print("  -> Synthetic files prepared for all 7 modalities.")

    # 4. Upload evidence files
    print("\n[4/8] Uploading evidence files to case...")
    evidence_uploads = [
        ("invoice.png", png_bytes, "image/png"),
        ("audio_intercept.wav", wav_bytes, "audio/wav"),
        ("intelligence_report.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("chat_export.json", chat_json, "application/json"),
        ("transactions.csv", csv_bytes, "text/csv"),
        ("email_record.eml", eml_bytes, "message/rfc822"),
        ("whatsapp_log.txt", txt_bytes, "text/plain"),
    ]

    for fname, data, mime in evidence_uploads:
        res = post_multipart(
            f"{API_BASE}/cases/{case_id}/evidence",
            {"notes": f"Automated test upload of {fname}"},
            [("files", fname, data, mime)],
        )
        assert len(res) == 1
        item = res[0]
        print(f"  -> Uploaded '{fname}': SHA-256 = {item['sha256'][:12]}..., Type = {item['file_type']}")
        if item.get("extracted_text"):
            print(f"     Extracted: {repr(item['extracted_text'][:60])} (conf: {item.get('extraction_confidence')})")

    # 5. Verify all evidence in case
    print("\n[5/8] Fetching case evidence records...")
    case_evidence = get_json(f"{API_BASE}/cases/{case_id}/evidence")
    assert len(case_evidence) == 7, f"Expected 7 evidence items, got {len(case_evidence)}"
    for ev in case_evidence:
        assert ev["sha256"] is not None
        assert ev["authenticity_passed"] is True
    print(f"  -> All {len(case_evidence)} evidence files verified in case with SHA-256 fingerprints!")

    # 6. Run GLiNER + RapidFuzz Entity Matching
    print("\n[6/8] Executing GLiNER + RapidFuzz cross-evidence entity matching...")
    match_results = post_json(f"{API_BASE}/cases/{case_id}/entities/match", {})
    assert len(match_results) > 0, "No candidate matches generated!"
    print(f"  -> Generated {len(match_results)} candidate entity clusters.")

    # Inspect top clusters
    for cand in match_results:
        distinct_files = {m["filename"] for m in cand["mentions"]}
        print(f"     [{cand['entity_type']}] '{cand['canonical_name']}' - {cand['similarity_score']}% similarity across {len(distinct_files)} file(s)")

    # Verify cross-evidence candidate for Marcus Vance
    canonical_names = [c["canonical_name"].lower() for c in match_results]
    assert any("marcus" in name or "vance" in name for name in canonical_names), f"Missing Marcus Vance in {canonical_names}"
    assert any("elena" in name or "rostova" in name for name in canonical_names), f"Missing Elena Rostova in {canonical_names}"
    print("  -> Cross-evidence identity clustering confirmed for primary targets!")

    # 7. Test Human Review Lifecycle
    print("\n[7/8] Testing human review actions (confirm, separate, reject, undo)...")
    target_match = match_results[0]
    match_id = target_match["id"]

    # Confirm
    conf_res = post_json(f"{API_BASE}/entities/matches/{match_id}/review", {"action": "confirm", "review_notes": "Analyst verified match"})
    assert conf_res["status"] == "confirmed"
    print("  -> Confirm action verified: status is 'confirmed'")

    # Mark Separate
    sep_res = post_json(f"{API_BASE}/entities/matches/{match_id}/review", {"action": "separate", "review_notes": "Distinct personas"})
    assert sep_res["status"] == "separate"
    print("  -> Separate action verified: status is 'separate'")

    # Reject
    rej_res = post_json(f"{API_BASE}/entities/matches/{match_id}/review", {"action": "reject"})
    assert rej_res["status"] == "rejected"
    print("  -> Reject action verified: status is 'rejected'")

    # Undo
    undo_res = post_json(f"{API_BASE}/entities/matches/{match_id}/review", {"action": "undo"})
    assert undo_res["status"] == "pending"
    print("  -> Undo action verified: status is 'pending'")

    # 8. Check Audit Logs
    print("\n[8/8] Verifying forensic audit logs...")
    audit_logs = get_json(f"{API_BASE}/cases/{case_id}/audit-logs")
    actions = [l["action"] for l in audit_logs]
    print(f"  -> Audit log contains {len(audit_logs)} forensic entries: {set(actions)}")
    assert any("UPLOAD" in a for a in actions)
    assert "ENTITY_REVIEW_CONFIRM" in actions
    assert "ENTITY_REVIEW_SEPARATE" in actions
    assert "ENTITY_REVIEW_REJECT" in actions

    print("\n=======================================================")
    print(">>> ALL 8/8 INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
    print("=======================================================\n")


if __name__ == "__main__":
    run_all_tests()
