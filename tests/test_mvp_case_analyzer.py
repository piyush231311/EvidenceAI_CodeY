"""
Test Suite for Evidence AI Core MVP Case Analyzer.
Validates:
  1. Case B (Banking / KYC scheme)
  2. Case A (Invoice KL-8842 / Corporate coercion)
  3. Preliminary Narrative: 150-250 words
  4. Evidence-backed facts: 5-10 facts with verbatim quotes & source files
  5. Unresolved questions: 3-5 questions with topics, why it matters, options
  6. Final report narrative incorporating user answers: 200-350 words
"""

import pytest
from src.intelligence.case_analyzer import analyze_case_mvp, generate_mvp_final_report_narrative


CASE_B_EVIDENCE = [
    {
        "id": "ev_b1",
        "original_filename": "Mahati_Bank_Statement.pdf",
        "file_type": "text",
        "extracted_text": (
            "MAHATI BANK LIMITED\nSTATEMENT OF ACCOUNT\n"
            "Account Holder: Ms. Neha Kulkarni\nAccount Number: XXXX-XXXX-4921\nStatement Period: 01 Nov 2026 to 15 Nov 2026\n"
            "Date | Description | Ref | Debit | Credit | Balance\n"
            "09 Nov 2026\nUPI-DEBIT-JIFFY WALLET\nUPI3928104821\n48,000.00\n\n94,850.50\n"
            "09 Nov 2026\nUPI-DEBIT-JIFFY WALLET\nUPI3928104953\n22,500.00\n\n72,350.50\n"
            "10 Nov 2026\nSALARY-CREDIT\nSAL88391011\n\n85,000.00\n157,350.50\n"
        )
    },
    {
        "id": "ev_b2",
        "original_filename": "Urgent_Notice_Email.eml",
        "file_type": "text",
        "extracted_text": (
            "Date: Sat, 14 Nov 2026 11:24:00 +0530\nFrom: support@mahati-bank-secure.com\nTo: neha.kulkarni@gmail.com\n"
            "Subject: URGENT: Your Mahati Bank Account Has Been Temporarily Frozen\n\n"
            "Dear Customer, Suspicious debit activity was detected on your account. Periodic KYC verification is overdue. "
            "Your account will be suspended within 24 hours unless you verify identity."
        )
    },
    {
        "id": "ev_b3",
        "original_filename": "SMS_Alert_Screenshot.png",
        "file_type": "image",
        "extracted_text": (
            "VM-MAHATI\n14 Nov 2026, 2:40 PM\n"
            "Dear Customer, Your Mahati Bank KYC has expired today. Your netbanking services will be deactivated. "
            "Click here to update immediately: http://mahati-kyc-update.in/verify"
        )
    },
    {
        "id": "ev_b4",
        "original_filename": "Phishing_Portal_Screenshot.png",
        "file_type": "image",
        "extracted_text": (
            "Not Secure — mahati-kyc-update.in/verify\n"
            "Mahati Bank - Customer Verification Portal\n"
            "Please enter your Customer ID, Registered Mobile Number, and Password to verify KYC."
        )
    },
    {
        "id": "ev_b5",
        "original_filename": "Phone_Call_Transcript.txt",
        "file_type": "text",
        "extracted_text": (
            "Recorded Intercept Call - Saturday, 14 Nov 2026\n"
            "Caller: Hello sir, Mahati Bank KYC department. Am I speaking with Arjun Menon?\n"
            "Recipient: Yes, speaking. I updated my KYC on the link this morning.\n"
            "Caller: Yes sir, we received it, but the OTP verification is incomplete. Your account will be blocked today.\n"
            "Recipient: Blocked? But I filled everything in.\n"
            "Caller: One OTP has just been sent to your mobile. Please read it out so I can complete the update.\n"
            "Recipient: Okay, it's 7, 4, 1, 9, 6, 2.\n"
            "Caller: Verification code received. Your KYC is updated."
        )
    }
]

CASE_A_EVIDENCE = [
    {
        "id": "ev_a1",
        "original_filename": "WhatsApp_Chat_20261112.txt",
        "file_type": "text",
        "extracted_text": (
            "[12/11/26, 10:14 AM] Vikram Nair: Rohan, answer my calls. Audit is tomorrow.\n"
            "[12/11/26, 10:17 AM] Vikram Nair: Invoice KL-8842 is still pending approval.\n"
            "[12/11/26, 10:21 AM] Rohan Deshmukh: I cannot approve 21.8L for fake shipments.\n"
            "[12/11/26, 10:23 AM] Vikram Nair: You took your share. March and July manifests have your signature.\n"
            "[12/11/26, 10:28 AM] Rohan Deshmukh: That cash was a loan. You forged my access.\n"
            "[12/11/26, 10:33 AM] Rohan Deshmukh: Portal needs hardware token. I don't have it.\n"
            "[12/11/26, 10:40 AM] Vikram Nair: Meet me at Cubbon Park near Queen Victoria gate at 4:30 PM.\n"
            "[12/11/26, 10:42 AM] Rohan Deshmukh: 4:30 PM is impossible. 5:15 PM earliest.\n"
            "[12/11/26, 10:43 AM] Vikram Nair: Fine. 5:15 PM sharp. Bring token."
        )
    },
    {
        "id": "ev_a2",
        "original_filename": "Invoice_KL8842.png",
        "file_type": "image",
        "extracted_text": (
            "INVOICE KL-8842\nKaveri Supply & Logistics\nClient: NexaTech Solutions\n"
            "Date: 12-Nov-2026\nSubtotal: INR 18,50,000\nGST (18%): INR 3,33,000\n"
            "Grand Total: INR 21,83,000\nStatus: OVERDUE\n"
            "Handwritten Note: Verified & Approved - Rohan D. 12/11/26 4:30 PM"
        )
    },
    {
        "id": "ev_a3",
        "original_filename": "Email_Notice.eml",
        "file_type": "text",
        "extracted_text": (
            "Date: Thu, 12 Nov 2026 10:14:00 +0530\nFrom: vikram@kaveri-logistics.com\nTo: rohan@nexatech.com\n"
            "Subject: Urgent: KL-8842 Approval Before Audit\n\n"
            "Rohan, approve KL-8842 before 6 PM today or external auditors will pull March and July records. "
            "Think about your family."
        )
    }
]


def test_case_b_mvp_analysis():
    """Verify Case B produces 150-250 word narrative, 5-10 facts with citations, and 3-5 questions."""
    res = analyze_case_mvp("case_b", CASE_B_EVIDENCE, timeline_scheduled_count=15)

    assert res.case_domain == "banking_fraud"
    assert "Unauthorized UPI" in res.case_title
    
    # 1. Narrative word count check (150-250 words)
    words = res.preliminary_narrative.split()
    assert 140 <= len(words) <= 260, f"Narrative words: {len(words)}, expected ~150-250"
    assert "Neha Kulkarni" in res.preliminary_narrative
    assert "Jiffy Wallet" in res.preliminary_narrative
    assert "70,500" in res.preliminary_narrative
    assert "741962" in res.preliminary_narrative

    # 2. Evidence-backed facts check (5 to 10 facts)
    assert 5 <= len(res.evidence_backed_facts) <= 10, f"Facts count: {len(res.evidence_backed_facts)}"
    for f in res.evidence_backed_facts:
        assert f.citation.verbatim_quote, "Every fact must have a verbatim quote"
        assert f.citation.filename, "Every fact must cite the source filename"
        assert f.citation.evidence_id, "Every fact must cite the evidence_id"

    # 3. Contextual questions check (3 to 5 questions)
    assert 3 <= len(res.unresolved_questions) <= 5, f"Questions count: {len(res.unresolved_questions)}"
    q_topics = [q.topic.lower() for q in res.unresolved_questions]
    assert any("otp" in t for t in q_topics), "Must ask about OTP disclosure"
    assert any("jiffy" in t or "debit" in t for t in q_topics), "Must ask about Jiffy Wallet debits"
    assert any("phishing" in t or "link" in t or "sms" in t for t in q_topics), "Must ask about phishing link"

    for q in res.unresolved_questions:
        assert q.why_it_matters, "Every question must state why it matters"
        assert len(q.options) >= 3, "Every question must have at least 3 options"
        assert any("not sure" in o.lower() or "not know" in o.lower() or "unsure" in o.lower() for o in q.options), (
            "Every question must have an unknown/not-sure option"
        )


def test_case_a_mvp_analysis():
    """Verify Case A produces 150-250 word narrative, 5-10 facts with citations, and 3-5 questions."""
    res = analyze_case_mvp("case_a", CASE_A_EVIDENCE, timeline_scheduled_count=5)

    assert res.case_domain == "corporate_coercion"
    assert "KL-8842" in res.case_title

    words = res.preliminary_narrative.split()
    assert 140 <= len(words) <= 260, f"Narrative words: {len(words)}, expected ~150-250"
    assert "Vikram Nair" in res.preliminary_narrative
    assert "Rohan Deshmukh" in res.preliminary_narrative
    assert "KL-8842" in res.preliminary_narrative

    assert 5 <= len(res.evidence_backed_facts) <= 10
    assert 3 <= len(res.unresolved_questions) <= 5


def test_mvp_final_report_narrative_integration():
    """Verify user answers are naturally woven into a 200-350 word final narrative."""
    res = analyze_case_mvp("case_b", CASE_B_EVIDENCE, timeline_scheduled_count=15)
    
    sample_answers = [
        {
            "selected_option": "I read out the OTP to someone over the phone",
            "free_text_clarification": "The caller sounded official and insisted my account would be frozen immediately.",
            "user_surety": "Very sure",
            "knowledge_basis": "Personally participated",
        },
        {
            "selected_option": "I did not authorize or recognize either transaction",
            "free_text_clarification": "I only learned of Jiffy Wallet when reviewing my bank statement.",
            "user_surety": "Very sure",
            "knowledge_basis": "Personally participated",
        }
    ]

    report = generate_mvp_final_report_narrative(res, sample_answers)
    final_text = report["final_narrative"]
    words = final_text.split()

    assert 190 <= len(words) <= 360, f"Final report words: {len(words)}, expected ~200-350"
    assert "Following investigator inquiry" in final_text
    assert "read out the OTP" in final_text
    assert "did not authorize" in final_text
    assert report["updated_with_clarifications"] is True
    assert report["clarification_count"] == 2
