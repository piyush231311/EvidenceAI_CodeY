"""
Comprehensive Verification Test Suite for Evidence AI Case Understanding,
Chronological Event Reconstruction, Contextual Quiz, and Forensic Incident Reporting.

Verifies:
  1. Case A (Invoice KL-8842 Coercion)
  2. Case B (5-File Banking Fraud & KYC Phishing)
  3. Dynamic narrative updates with user quiz answers
  4. 3-Section Report Structure:
     - Section A: What appears to have happened?
     - Section B: What remains unclear?
     - Section C: What additional information would help?
  5. Expandable Technical Appendix
"""

import pytest
from datetime import datetime

from src.intelligence.event_extractor import deterministic_grounded_event_extraction, EventCandidate
from src.intelligence.timeline_builder import build_timeline_from_events
from src.intelligence.evidence_reasoner import analyze_cross_evidence_relationships
from src.intelligence.clarification_engine import (
    generate_clarification_quiz,
    apply_clarifications_to_timeline,
    UserAnswer,
    ClarificationQuestion,
)
from src.intelligence.case_understanding import generate_case_understanding, analyze_case_domain
from src.reporting.report_generator import generate_forensic_incident_report, render_incident_report_html


class DummyEvidence:
    def __init__(self, evid_id, filename, file_type, text):
        self.id = evid_id
        self.original_filename = filename
        self.file_type = file_type
        self.extracted_text = text
        self.sha256 = f"dummy_sha_{evid_id}"
        self.size_bytes = len(text)
        self.extraction_confidence = 0.95


# -------------------------------------------------------------
# CASE A FIXTURES (Invoice KL-8842 & Alleged Coercion)
# -------------------------------------------------------------
CASE_A_FILES = [
    DummyEvidence(
        "ev_a1", "WhatsApp_Chat_20261112.txt", "text",
        "[12/11/26, 10:14 AM] Vikram Nair: Rohan, answer my calls. Audit is tomorrow.\n"
        "[12/11/26, 10:17 AM] Vikram Nair: Invoice KL-8842 is still pending approval.\n"
        "[12/11/26, 10:21 AM] Rohan Deshmukh: I cannot approve 21.8L for fake shipments.\n"
        "[12/11/26, 10:23 AM] Vikram Nair: You took your share. March and July manifests have your signature.\n"
        "[12/11/26, 10:28 AM] Rohan Deshmukh: That cash was a loan. You forged my access.\n"
        "[12/11/26, 10:33 AM] Rohan Deshmukh: Portal needs hardware token. I don't have it.\n"
        "[12/11/26, 10:40 AM] Vikram Nair: Meet me at Cubbon Park near Queen Victoria gate at 4:30 PM.\n"
        "[12/11/26, 10:42 AM] Rohan Deshmukh: 4:30 PM is impossible. 5:15 PM earliest.\n"
        "[12/11/26, 10:43 AM] Vikram Nair: Fine. 5:15 PM sharp. Bring token."
    ),
    DummyEvidence(
        "ev_a2", "Invoice_KL8842.png", "image",
        "INVOICE KL-8842\nKaveri Supply & Logistics\nClient: NexaTech Solutions\n"
        "Date: 12-Nov-2026\nSubtotal: INR 18,50,000\nGST (18%): INR 3,33,000\n"
        "Grand Total: INR 21,83,000\nStatus: OVERDUE\n"
        "Handwritten Note: Verified & Approved - Rohan D. 12/11/26 4:30 PM"
    ),
    DummyEvidence(
        "ev_a3", "Email_Notice.eml", "text",
        "Date: Thu, 12 Nov 2026 10:14:00 +0530\nFrom: vikram@kaveri-logistics.com\nTo: rohan@nexatech.com\n"
        "Subject: Urgent: KL-8842 Approval Before Audit\n\n"
        "Rohan, approve KL-8842 before 6 PM today or external auditors will pull March and July records. "
        "Think about your family."
    )
]


# -------------------------------------------------------------
# CASE B FIXTURES (Mahati Bank KYC Fraud)
# -------------------------------------------------------------
CASE_B_FILES = [
    DummyEvidence(
        "ev_b1", "Mahati_Bank_Statement.pdf", "text",
        "MAHATI BANK LIMITED\nSTATEMENT OF ACCOUNT\n"
        "Account Holder: Ms. Neha Kulkarni\nAccount Number: XXXX-XXXX-4921\nStatement Period: 01 Nov 2026 to 15 Nov 2026\n"
        "Date | Description | Ref | Debit | Credit | Balance\n"
        "09 Nov 2026\nUPI-DEBIT-JIFFY WALLET\nUPI3928104821\n48,000.00\n\n94,850.50\n"
        "09 Nov 2026\nUPI-DEBIT-JIFFY WALLET\nUPI3928104992\n22,500.00\n\n72,350.50\n"
        "10 Nov 2026\nSALARY-CREDIT\nSAL88391011\n\n85,000.00\n157,350.50\n"
    ),
    DummyEvidence(
        "ev_b2", "Urgent_Notice_Email.eml", "text",
        "Date: Sat, 14 Nov 2026 11:24:00 +0530\nFrom: support@mahati-bank-secure.com\nTo: neha.kulkarni@gmail.com\n"
        "Subject: URGENT: Your Mahati Bank Account Has Been Temporarily Frozen\n\n"
        "Dear Customer, Suspicious debit activity was detected on your account. Periodic KYC verification is overdue. "
        "Your account will be suspended within 24 hours unless you verify identity."
    ),
    DummyEvidence(
        "ev_b3", "SMS_Alert_Screenshot.png", "image",
        "VM-MAHATI\n14 Nov 2026, 2:40 PM\n"
        "Dear Customer, Your Mahati Bank KYC has expired today. Your netbanking services will be deactivated. "
        "Click here to update immediately: http://mahati-kyc-update.in/verify"
    ),
    DummyEvidence(
        "ev_b4", "Phishing_Portal_Screenshot.png", "image",
        "Not Secure — mahati-kyc-update.in/verify\n"
        "Mahati Bank - Customer Verification Portal\n"
        "Please enter your Customer ID, Registered Mobile Number, and Password to verify KYC."
    ),
    DummyEvidence(
        "ev_b5", "Phone_Call_Transcript.txt", "text",
        "Recorded Intercept Call - Saturday, 14 Nov 2026\n"
        "Caller: Hello Madam, I am calling from Mahati Bank KYC verification division regarding your account 4921.\n"
        "Recipient: Yes, I got an SMS saying my account will be closed.\n"
        "Caller: Exactly. To reactivate it right now, please read out the 6-digit OTP code sent to your mobile.\n"
        "Recipient: Okay, the code is 741962.\n"
        "Caller: Verification code received. Your KYC is updated."
    )
]


def test_case_b_extracts_scheduled_events_not_zero():
    """Verify Case B produces multiple sequentially anchored events (resolving the 0-event bug)."""
    all_events = []
    for ef in CASE_B_FILES:
        evs = deterministic_grounded_event_extraction(
            text=ef.extracted_text,
            case_id="case_b",
            evidence_id=ef.id,
            filename=ef.original_filename,
        )
        all_events.extend(evs)

    assert len(all_events) >= 5, f"Expected at least 5 event candidates, got {len(all_events)}"

    timeline = build_timeline_from_events(all_events, case_id="case_b")

    # Critical check: scheduled_events must NOT be 0!
    assert len(timeline.scheduled_events) >= 6, (
        f"Critical failure: scheduled_events is {len(timeline.scheduled_events)}, expected >= 6"
    )

    # Verify Jiffy Wallet transactions are captured in timeline
    titles = [e.title for e in timeline.scheduled_events]
    has_jiffy = any("jiffy wallet" in t.lower() or "48,000" in t or "22,500" in t for t in titles)
    assert has_jiffy, "Expected Jiffy Wallet UPI debits to be chronologically anchored"

    # Verify SMS / Phishing / Call events are captured
    has_sms = any("sms" in t.lower() or "kyc" in t.lower() for t in titles)
    assert has_sms, "Expected SMS / KYC events in scheduled timeline"


def test_case_a_and_b_domain_understanding():
    """Verify domain classification correctly identifies corporate coercion vs banking fraud."""
    text_a = " ".join(f.extracted_text for f in CASE_A_FILES)
    text_b = " ".join(f.extracted_text for f in CASE_B_FILES)

    assert analyze_case_domain(text_a, []) == "corporate_coercion"
    assert analyze_case_domain(text_b, []) == "banking_fraud"


def test_case_b_case_understanding_three_sections():
    """Verify Case B generates the required 3-section readable output."""
    all_events = []
    for ef in CASE_B_FILES:
        evs = deterministic_grounded_event_extraction(ef.extracted_text, "case_b", ef.id, ef.original_filename)
        all_events.extend(evs)
    timeline = build_timeline_from_events(all_events, case_id="case_b")
    reasoning = analyze_cross_evidence_relationships(all_events, timeline)

    cu = generate_case_understanding("case_b", CASE_B_FILES, all_events, timeline, reasoning.contradictions)

    # 1. Section A: What appears to have happened?
    assert len(cu.what_happened) >= 200, "What happened narrative must be comprehensive (>= 200 chars)"
    assert "Neha Kulkarni" in cu.what_happened or "Mahati Bank" in cu.what_happened
    assert "70,500" in cu.what_happened or "Jiffy Wallet" in cu.what_happened

    # 2. Section B: What remains unclear?
    assert 3 <= len(cu.what_remains_unclear) <= 6, f"Expected 3-5 unclear items, got {len(cu.what_remains_unclear)}"
    unclear_text = " ".join(cu.what_remains_unclear).lower()
    assert "otp" in unclear_text or "debit" in unclear_text or "link" in unclear_text

    # 3. Section C: What additional information would help?
    assert len(cu.what_would_help) >= 3, "Expected at least 3 helpful action items"


def test_contextual_quiz_generation():
    """Verify questions are targeted and context-grounded with proper defaults."""
    all_events_b = []
    for ef in CASE_B_FILES:
        evs = deterministic_grounded_event_extraction(ef.extracted_text, "case_b", ef.id, ef.original_filename)
        all_events_b.extend(evs)
    timeline_b = build_timeline_from_events(all_events_b, case_id="case_b")
    reasoning_b = analyze_cross_evidence_relationships(all_events_b, timeline_b)

    questions_b = generate_clarification_quiz(
        case_id="case_b",
        contradictions=reasoning_b.contradictions,
        timeline=timeline_b,
        evidence_files=CASE_B_FILES,
        events=all_events_b,
    )

    assert len(questions_b) >= 2, "Expected at least 2 contextual questions for Case B"
    prompts_b = " ".join(q.prompt for q in questions_b).lower()
    assert "otp" in prompts_b or "jiffy wallet" in prompts_b or "link" in prompts_b

    # Verify all questions contain neutral "Not sure" or "Did not witness" options
    for q in questions_b:
        assert any("not sure" in opt.lower() or "don't know" in opt.lower() or "did not" in opt.lower() for opt in q.options), (
            f"Question {q.prompt} missing neutral option"
        )


def test_dynamic_narrative_updates_with_quiz_answers():
    """Verify report narrative dynamically updates when user submits clarification answers."""
    all_events_b = []
    for ef in CASE_B_FILES:
        evs = deterministic_grounded_event_extraction(ef.extracted_text, "case_b", ef.id, ef.original_filename)
        all_events_b.extend(evs)
    timeline_b = build_timeline_from_events(all_events_b, case_id="case_b")
    reasoning_b = analyze_cross_evidence_relationships(all_events_b, timeline_b)

    # Initial report without user answers
    report_initial = generate_forensic_incident_report(
        case_id="case_b",
        evidence_files=[{"id": f.id, "original_filename": f.original_filename, "file_type": f.file_type, "sha256": f.sha256, "extracted_text": f.extracted_text} for f in CASE_B_FILES],
        timeline=timeline_b,
        contradictions=reasoning_b.contradictions,
        questions=[],
        answers=[],
    )
    assert not report_initial.updated_with_clarifications

    # User answers: clarifies Jiffy Wallet was NEVER authorized and OTP was read under duress
    user_answers = [
        UserAnswer(
            answer_id="ans_1",
            question_id="q_jiffy",
            case_id="case_b",
            selected_option="I did not authorize or recognize either transaction to Jiffy Wallet",
            free_text_clarification="I have never used Jiffy Wallet. I only discovered this from the bank statement.",
            user_surety="Very sure",
            surety_score=4,
            knowledge_basis="Personally participated",
        ),
        UserAnswer(
            answer_id="ans_2",
            question_id="q_otp",
            case_id="case_b",
            selected_option="I disclosed code 741962 because the caller claimed account would be deleted",
            free_text_clarification="The caller sounded very authentic and had my name and partial account number.",
            user_surety="Very sure",
            surety_score=4,
            knowledge_basis="Directly witnessed",
        )
    ]

    report_updated = generate_forensic_incident_report(
        case_id="case_b",
        evidence_files=[{"id": f.id, "original_filename": f.original_filename, "file_type": f.file_type, "sha256": f.sha256, "extracted_text": f.extracted_text} for f in CASE_B_FILES],
        timeline=timeline_b,
        contradictions=reasoning_b.contradictions,
        questions=[
            ClarificationQuestion(question_id="q_jiffy", case_id="case_b", question_type="fact", prompt="Did you authorize Jiffy Wallet debits?", context_excerpt="Statement", options=[], status="answered"),
            ClarificationQuestion(question_id="q_otp", case_id="case_b", question_type="fact", prompt="Did you disclose OTP 741962?", context_excerpt="Call transcript", options=[], status="answered"),
        ],
        answers=user_answers,
    )

    assert report_updated.updated_with_clarifications is True
    # The narrative or user clarifications must now reflect the answers
    assert len(report_updated.user_clarifications) == 2
    assert "Jiffy Wallet" in report_updated.what_happened or any("Jiffy Wallet" in c["selected_option"] for c in report_updated.user_clarifications)

    html_preview = render_incident_report_html(report_updated)
    assert "Refined by Witness Testimony" in html_preview
    assert "Section A. What Appears to Have Happened?" in html_preview
    assert "Section B. What Remains Unclear?" in html_preview
    assert "Section C. What Additional Information Would Help?" in html_preview
    assert "Technical Appendix" in html_preview


def test_case_a_full_report_generation():
    """Verify Case A produces comprehensive 3-section report with Technical Appendix."""
    all_events_a = []
    for ef in CASE_A_FILES:
        evs = deterministic_grounded_event_extraction(ef.extracted_text, "case_a", ef.id, ef.original_filename)
        all_events_a.extend(evs)
    timeline_a = build_timeline_from_events(all_events_a, case_id="case_a")
    reasoning_a = analyze_cross_evidence_relationships(all_events_a, timeline_a)

    report_a = generate_forensic_incident_report(
        case_id="case_a",
        evidence_files=[{"id": f.id, "original_filename": f.original_filename, "file_type": f.file_type, "sha256": f.sha256, "extracted_text": f.extracted_text} for f in CASE_A_FILES],
        timeline=timeline_a,
        contradictions=reasoning_a.contradictions,
        questions=[],
        answers=[],
    )

    assert report_a.case_title == "Disputed Invoice KL-8842 and Alleged Coercion"
    assert "Vikram Nair" in report_a.what_happened
    assert "Rohan Deshmukh" in report_a.what_happened
    assert len(report_a.what_remains_unclear) >= 3
    assert len(report_a.what_would_help) >= 3
    assert len(report_a.chronological_timeline) >= 5

    html_a = render_incident_report_html(report_a)
    assert "Disputed Invoice KL-8842" in html_a
    assert "Section A. What Appears to Have Happened?" in html_a
    assert "Section B. What Remains Unclear?" in html_a
    assert "Section C. What Additional Information Would Help?" in html_a
    assert "Technical Appendix" in html_a
