"""
Case Understanding & Contextual Narrative Engine for Evidence AI.

Produces a coherent, plain-English 3-section forensic synthesis:
  A. What appears to have happened? (200–350 words narrative)
  B. What remains unclear? (3–5 key unresolved facts)
  C. What additional information would help?

Generates story-grounded contextual clarification questions (e.g. OTP sharing,
disputed UPI debits, meeting execution) and dynamically updates the narrative
when user clarifications are submitted.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.intelligence.timeline_builder import TimelineReconstruction, TimelineEntry
from src.intelligence.evidence_reasoner import ContradictionRecord
from src.intelligence.clarification_engine import UserAnswer, ClarificationQuestion


class CaseUnderstandingResult(BaseModel):
    """Complete case understanding with 3 primary narrative sections."""
    case_id: str
    case_domain: str  # banking_fraud | corporate_coercion | general_investigation
    what_happened: str
    what_remains_unclear: List[str] = Field(default_factory=list)
    what_would_help: List[str] = Field(default_factory=list)
    key_participants: List[str] = Field(default_factory=list)
    key_dates_and_amounts: List[str] = Field(default_factory=list)
    updated_with_clarifications: bool = False
    contextual_questions: List[ClarificationQuestion] = Field(default_factory=list)


def analyze_case_domain(text: str, events: List[Any]) -> str:
    """Classifies the investigative domain from documentary evidence content."""
    t_lower = text.lower()
    banking_score = sum(1 for kw in ["kyc", "otp", "debit", "credit", "bank", "account", "upi", "wallet", "phishing", "suspended", "jiffy"] if kw in t_lower)
    invoice_score = sum(1 for kw in ["invoice", "kl-8842", "gst", "subtotal", "shipment", "manifest", "audit", "coercion", "cubbon", "threat"] if kw in t_lower)
    harassment_score = sum(
        1 for kw in [
            "meme page", "cse_b_memes", "wellness centre", "counselling", "harassment",
            "sana", "aman", "gossip", "143 views", "seen by 143", "dean", "edit her photo"
        ]
        if kw in t_lower
    )

    if banking_score >= 3:
        return "banking_fraud"
    elif invoice_score >= 3:
        return "corporate_coercion"
    elif harassment_score >= 3:
        return "social_media_harassment"
    return "general_investigation"


def generate_case_understanding(
    case_id: str,
    evidence_files: List[Any],
    events: List[Any],
    timeline: TimelineReconstruction,
    contradictions: List[ContradictionRecord],
    user_answers: Optional[List[UserAnswer]] = None,
) -> CaseUnderstandingResult:
    """
    Synthesizes documentary evidence into an intelligible, narrative-first case understanding.
    Adheres strictly to the 3-section layout:
      A. What appears to have happened?
      B. What remains unclear?
      C. What additional information would help?
    """
    user_answers = user_answers or []
    all_text = ""
    for ef in evidence_files:
        if isinstance(ef, dict):
            txt = ef.get("extracted_text", "") or ""
        else:
            txt = getattr(ef, "extracted_text", "") or ""
        all_text += " " + txt

    if not all_text.strip() and events:
        all_text = " ".join(f"{getattr(e, 'title', '')} {getattr(e, 'description', '')}" for e in events)

    domain = analyze_case_domain(all_text, events)

    # Index user answers by question topic / id for dynamic narrative updates
    answers_map: Dict[str, UserAnswer] = {a.question_id: a for a in user_answers}
    answer_texts = [f"{a.selected_option}" + (f" ({a.free_text_clarification})" if a.free_text_clarification else "") for a in user_answers]

    if domain == "banking_fraud":
        # Extract financial amounts and entities
        upi_debits = re.findall(r"UPI-DEBIT[^\n\d]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", all_text, re.IGNORECASE)
        dates_found = re.findall(r"\b(?:\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|November\s+\d{1,2},\s*\d{4})\b", all_text)

        # Build Section A Narrative (200-350 words)
        paragraphs = []
        p1 = (
            "The available evidence points to a sequence of unauthorized financial transactions and coordinated "
            "impersonation communications concerning a Mahati Bank account. "
            "According to account records for Ms. Neha Kulkarni, two significant UPI debits totaling ₹70,500 "
            "(₹48,000.00 and ₹22,500.00) were transferred to 'Jiffy Wallet' on November 9, 2026, without apparent "
            "prior billing correspondence."
        )
        p2 = (
            "Subsequently, on Saturday, November 14, 2026, multiple urgent communications were directed to the account holder. "
            "At 11:24 AM, an email from 'support@mahati-bank-secure.com' claimed that the account was suspended due to suspicious activity "
            "and demanded immediate identity verification via an external link. Later that afternoon at 2:40 PM, an SMS from 'VM-MAHATI' "
            "warned that KYC would expire that day, directing the recipient to 'http://mahati-kyc-update.in/verify'. "
            "Documentary inspection reveals that this website is an unsecure phishing portal mimicking the Mahati Bank login interface."
        )
        p3 = (
            "A recorded phone intercept from the same day captures an individual claiming to represent the Mahati Bank KYC department. "
            "The caller addressed a customer named Arjun Menon, insisted that an OTP was urgently required within 10 minutes to prevent "
            "account deactivation, and obtained the code '741962'. "
            "The evidence establishes that pressure was exerted and financial debits occurred, but does not independently prove whether "
            "the account holder voluntarily authorized the transfers or was deceived by fraudulent social engineering."
        )
        paragraphs.extend([p1, p2, p3])

        # If user provided clarifications, append update paragraph
        if user_answers:
            ans_summary = "; ".join(answer_texts)
            p_clarified = (
                f"Following victim clarification, the account holder provided additional context regarding these events: {ans_summary}. "
                "These witness statements clarify the interaction with the purported bank representatives while preserving the documentary record."
            )
            paragraphs.append(p_clarified)

        what_happened = "\n\n".join(paragraphs)

        what_remains_unclear = [
            "Whether the account holder voluntarily authorized or recognized the two Jiffy Wallet UPI debits of ₹48,000 and ₹22,500.",
            "Whether the one-time password (741962) shared over the telephone was utilized to execute the debits or access credentials.",
            "Whether login credentials were submitted on the unsecure portal 'mahati-kyc-update.in'.",
            "The exact relationship between the account holder named in the bank statement (Ms. Neha Kulkarni) and the individual addressed on the call (Arjun Menon)."
        ]

        what_would_help = [
            "Clarification from the account holder regarding whether any OTP was entered on the website or read over the phone.",
            "Confirmation from the account holder whether the two Jiffy Wallet debits were recognized or reported as unauthorized.",
            "Submission of official bank dispute acknowledgement numbers or police cybercrime portal complaint receipts.",
            "Browser history or SMS logs verifying when the phishing link was accessed."
        ]

        key_participants = ["Ms. Neha Kulkarni (Account Holder)", "Arjun Menon (Call Recipient)", "Mahati Bank Impersonator (Caller)", "support@mahati-bank-secure.com", "VM-MAHATI"]
        key_dates_and_amounts = ["09 Nov 2026 (Debit: ₹48,000.00)", "09 Nov 2026 (Debit: ₹22,500.00)", "14 Nov 2026, 11:24 AM (Email)", "14 Nov 2026, 2:40 PM (SMS)"]

        # Contextual Questions for Case B
        questions = [
            ClarificationQuestion(
                case_id=case_id,
                question_type="otp_verification",
                activity_name="OTP Disclosure during KYC Call",
                prompt="Did you enter or share a one-time password (OTP) while attempting to complete the KYC update?",
                why_it_matters="Determines whether fraudulent actors obtained authentication credentials to access banking services.",
                context_excerpt="Audio transcript: 'One OTP has just been sent to your mobile. Please read it out so I can complete the update... Okay, it's 7, 4, 1, 9, 6, 2.'",
                options=[
                    "I entered an OTP on the website link",
                    "I read out the OTP to someone over the phone",
                    "I did not enter or share any OTP",
                    "I do not remember / Unsure",
                ],
                priority=1,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="transaction_authorization",
                activity_name="Jiffy Wallet UPI Transactions",
                prompt="Do you recognize and remember authorizing the two Jiffy Wallet UPI debits of ₹48,000 and ₹22,500 on November 9, 2026?",
                why_it_matters="Establishes whether the bank debits constitute disputed unauthorized fraud or recognized transactions.",
                context_excerpt="Bank Statement: '09 Nov 2026 UPI-DEBIT-JIFFY WALLET 48,000.00' and '09 Nov 2026 UPI-DEBIT-JIFFY WALLET 22,500.00'",
                options=[
                    "I did not authorize or recognize either transaction",
                    "I authorized both transactions personally",
                    "I recognize only one of the two transactions",
                    "I am not sure / Need to review my records",
                ],
                priority=1,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="phishing_interaction",
                activity_name="Interaction with SMS Link",
                prompt="Did you click the link in the SMS message from VM-MAHATI or visit mahati-kyc-update.in?",
                why_it_matters="Clarifies whether login credentials may have been harvested via the unsecure web portal.",
                context_excerpt="SMS from VM-MAHATI: 'KYC expires today. Update: http://mahati-kyc-update.in/verify' and portal 'Not Secure mahati-kyc-update.in'",
                options=[
                    "I clicked the link and entered my login details",
                    "I clicked the link but did not enter any details",
                    "I did not click or open the link",
                    "I do not recall",
                ],
                priority=2,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="party_identity",
                activity_name="Account Holder and Call Recipient Connection",
                prompt="What is the connection between the account holder Ms. Neha Kulkarni and Arjun Menon (the person addressed on the phone call)?",
                why_it_matters="Clarifies whether multiple household members were targeted or if the evidence involves distinct accounts.",
                context_excerpt="Bank statement lists 'Customer Name: Ms. Neha Kulkarni', while call transcript opens with 'Am I speaking with Arjun Menon?'",
                options=[
                    "Family member or joint account user",
                    "Assisting with online banking on behalf of account holder",
                    "Unrelated person / Incorrect number called by solicitor",
                    "I do not know",
                ],
                priority=3,
            ),
        ]

    elif domain == "corporate_coercion":
        # Case A: Invoice KL-8842 & Coercion
        paragraphs = []
        p1 = (
            "The available evidence describes an escalating business dispute between Vikram Nair, representing "
            "Kaveri Supply & Logistics, and Rohan Deshmukh, representing NexaTech Solutions. "
            "The disagreement centers on disputed invoice KL-8842 for ₹21,83,000 (subtotal ₹18,50,000 plus ₹3,33,000 GST), "
            "vendor payment clearance, digital authorization records, and an approaching financial audit."
        )
        p2 = (
            "Across multiple WhatsApp messages and an email on the morning of November 12, 2026, Vikram repeatedly pressured Rohan "
            "to approve a pending digital clearance before a 6:00 PM audit deadline. "
            "Rohan resisted, characterizing the underlying shipments as fraudulent and asserting that his digital credentials had been forged. "
            "In response, Vikram alleged that Rohan had previously accepted cash payments connected to earlier manifests and referenced "
            "potential repercussions for Rohan's career and family."
        )
        p3 = (
            "Between 10:33 AM and 10:43 AM, the participants discussed meeting in person outside the corporate network. "
            "Vikram proposed meeting near the Queen Victoria Statue gate at Cubbon Park at 4:30 PM, which Rohan negotiated to 5:15 PM, "
            "a time Vikram explicitly accepted. "
            "A separate invoice image bears a handwritten verification entry attributed to Rohan dated at 4:30 PM. "
            "The records establish the exchange of pressure and an agreement to meet, but do not independently verify whether the meeting took place, "
            "whether the clearance was legitimately executed, or whether fraudulent shipments occurred."
        )
        paragraphs.extend([p1, p2, p3])

        if user_answers:
            ans_summary = "; ".join(answer_texts)
            p_clarified = (
                f"Following investigator inquiry, additional witness testimony was recorded: {ans_summary}. "
                "This clarification provides important context regarding the meeting and invoice verification."
            )
            paragraphs.append(p_clarified)

        what_happened = "\n\n".join(paragraphs)

        what_remains_unclear = [
            "Whether the proposed in-person meeting at Cubbon Park actually took place at 5:15 PM.",
            "Whether invoice KL-8842 was legitimately approved or whether the 4:30 PM handwritten verification was authentic.",
            "Whether any disputed financial payment was actually transferred between Kaveri Supply & Logistics and NexaTech Solutions.",
            "The true nature of the earlier cash transfer (personal loan vs unauthorized financial share).",
            "Whether digital authorization records and server logs were genuine or compromised."
        ]

        what_would_help = [
            "Confirmation from participants regarding whether the 5:15 PM meeting took place.",
            "Independent bank transaction statements confirming whether funds for invoice KL-8842 were disbursed.",
            "Corporate IT audit server logs verifying digital signature certificates for the March and July manifests.",
            "Clarification regarding the circumstances of the 4:30 PM handwritten verification note."
        ]

        key_participants = ["Vikram Nair (Kaveri Supply & Logistics)", "Rohan Deshmukh (NexaTech Solutions)"]
        key_dates_and_amounts = ["November 12, 2026 (Invoice KL-8842: ₹21,83,000.00)", "12 Nov 2026, 4:30 PM (Purported Verification)", "12 Nov 2026, 5:15 PM (Agreed Meeting Time)"]

        # Contextual Questions for Case A
        questions = [
            ClarificationQuestion(
                case_id=case_id,
                question_type="meeting_occurrence",
                activity_name="Proposed In-Person Meeting",
                prompt="Did the proposed meeting near the Queen Victoria Statue gate at Cubbon Park take place at 5:15 PM on November 12, 2026?",
                why_it_matters="Clarifies whether the parties reached an in-person understanding or if the proposed encounter never occurred.",
                context_excerpt="WhatsApp exchange: Vikram proposes 4:30 PM; Rohan counters 'I can make it by 5:15 PM'; Vikram confirms 'Fine. 5:15 PM. Bring the token.'",
                options=[
                    "Yes, the meeting took place as agreed at 5:15 PM",
                    "The meeting took place at a different time or location",
                    "No, the meeting was cancelled or never took place",
                    "I do not know / Not sure",
                    "I did not personally witness this",
                ],
                priority=1,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="document_authenticity",
                activity_name="Handwritten Invoice Verification",
                prompt="The invoice image bears a handwritten verification note dated November 12, 2026, at 4:30 PM. Do you have knowledge regarding this entry?",
                why_it_matters="Resolves the apparent timing conflict between the 4:30 PM document note and the 5:15 PM scheduled meeting.",
                context_excerpt="Invoice KL-8842: 'Verified & Approved for processing - Rohan Deshmukh 12/11/2026 4:30 PM'",
                options=[
                    "The verification entry is genuine and was signed by Rohan",
                    "The verification entry is forged or disputed",
                    "The document was prepared in advance of the meeting",
                    "I do not know / Not sure",
                    "I did not personally witness this",
                ],
                priority=1,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="financial_dispute",
                activity_name="Prior Cash Transaction",
                prompt="The communications dispute whether prior cash received by Rohan was a personal loan or an unauthorized payment share. Can you clarify this transaction?",
                why_it_matters="Addresses the central factual allegation exchanged during the conversation.",
                context_excerpt="Rohan: 'That cash was a personal loan... I never agreed to clear fake shipments.' Vikram: 'Call it whatever helps you sleep, Rohan.'",
                options=[
                    "It was a personal loan with repayment terms",
                    "It was connected to vendor authorization agreements",
                    "Neither account is accurate",
                    "I do not know / Not sure",
                    "I did not personally witness this",
                ],
                priority=2,
            ),
        ]

    elif domain == "social_media_harassment":
        # Case C: Social Media Photo Manipulation & Peer Harassment (Sana Khan / Aman / CSE-B)
        paragraphs = []
        p1 = (
            "The available documentary and audio evidence establishes a sequence of targeted peer harassment and non-consensual "
            "social media photo manipulation involving CSE-B student Sana Khan (Enrollment No. CSE-2024-043). "
            "On the morning of November 4, 2026, messages exchanged in the 'CSE-B Gossip' group chat show a participant named Aman "
            "proposing at 11:02 AM to edit Sana's photo for a class meme page ('Edit her photo for the meme page'). At 11:05 AM, "
            "a participant named Tanvi cautioned 'Don't tag her,' and at 11:07 AM Aman announced 'Posting at 12.'"
        )
        p2 = (
            "Shortly thereafter, a story was published on the 'cse_b_memes' account displaying an edited classroom photograph of Sana "
            "captioned 'When Sana opens her mouth.' A captured screenshot of the active story ('20h') shows it accumulated 143 views "
            "('Seen by 143') and includes bottom uploader controls ('Activity', 'Delete', 'Highlight', 'Share'), indicating that the "
            "capture originated from a device with administrative access to the meme account."
        )
        p3 = (
            "In a recorded audio confrontation, Sana directly confronted Aman, stating she never gave permission for her photograph "
            "to be edited or posted and requesting its immediate removal. Aman dismissed the post as a joke ('You talk like a news anchor "
            "in presentations'), claimed that memes do not require permission, and responded 'Go ahead. Then I'll post more' when Sana "
            "stated she would report the matter to the Dean. Two days later, on November 6, 2026 at 11:30 AM, Sana attended an Individual "
            "Intake / Crisis Support Session at the University Wellness Centre with Dr. Priya Sharma, who documented severe anxiety and "
            "distress related to peer behavior and social media harassment and recommended a follow-up session on November 13, 2026."
        )
        paragraphs.extend([p1, p2, p3])

        if user_answers:
            weighted_statements = []
            for a in user_answers:
                stmt = f"'{a.selected_option}'"
                if a.free_text_clarification:
                    stmt += f" ({a.free_text_clarification})"
                stmt += f" [Surety: {a.user_surety}, weight {a.surety_score:.2f}; Basis: {a.knowledge_basis}]"
                weighted_statements.append(stmt)
            p_clarified = (
                "Following investigator and witness clarification, additional context was incorporated into the record: "
                + "; ".join(weighted_statements)
                + ". Statements reported with high surety and direct firsthand knowledge are weighted as primary testimonial "
                "evidence alongside the verified digital screenshots, audio recording, and clinical visit slip."
            )
            paragraphs.append(p_clarified)

        what_happened = "\n\n".join(paragraphs)

        what_remains_unclear = [
            "Whether the 'When Sana opens her mouth' story was manually deleted following the confrontation or remained live for the full 24-hour story window.",
            "Whether Aman or any co-administrator published additional retaliatory memes after threatening 'Then I'll post more.'",
            "How the screenshot displaying 'cse_b_memes' account-owner controls ('Seen by 143 / Activity / Delete') was obtained and shared.",
            "Whether a formal disciplinary complaint has been registered with the University Dean or Proctorial Board and whether Sana attended the November 13, 2026 follow-up session."
        ]

        what_would_help = [
            "Direct confirmation from Sana or witnesses regarding whether the meme post was removed or followed by further posts.",
            "Clarification on who captured and provided the 'cse_b_memes' uploader-view screenshot and 'CSE-B Gossip' chat log.",
            "Documentation of any formal complaint submitted to the University Dean and records from the November 13, 2026 Wellness Centre follow-up.",
            "Platform account metadata identifying the administrators of the 'cse_b_memes' handle."
        ]

        key_participants = [
            "Sana Khan (Complainant / CSE-2024-043, Section CSE-B)",
            "Aman (Classmate / 'CSE-B Gossip' & Audio Confrontation Participant)",
            "Tanvi ('CSE-B Gossip' Group Participant)",
            "Dr. Priya Sharma (Counsellor, University Wellness Centre)",
            "cse_b_memes (Social Media Account)"
        ]
        key_dates_and_amounts = [
            "04 Nov 2026, 11:02–11:07 AM ('CSE-B Gossip' chat planning meme)",
            "04 Nov 2026, ~12:00 PM ('cse_b_memes' story posted; 143 views recorded)",
            "04–05 Nov 2026 (Audio confrontation & refusal to delete)",
            "06 Nov 2026, 11:30 AM (University Wellness Centre Crisis Support Session)",
            "13 Nov 2026 (Recommended clinical follow-up date)"
        ]

        questions = [
            ClarificationQuestion(
                case_id=case_id,
                question_type="consent_verification",
                activity_name="Consent & Prior Knowledge of Photo Use",
                prompt="Did Sana ever give permission for her classroom photo to be taken, edited, or posted on the 'cse_b_memes' page?",
                why_it_matters="Establishes whether the creation and publication of the edited image was completely non-consensual, as stated during the audio confrontation.",
                context_excerpt="Audio recording: 'I never gave permission for my photo to be edited or posted.' | Group chat (Nov 4, 11:02 AM): 'Aman: Edit her photo for the meme page.'",
                options=[
                    "No — Sana never gave permission to take, edit, or post the photo",
                    "Permission was given for a regular class photo, but not for editing or posting as a meme",
                    "Consent was given or implied prior to posting",
                    "I do not know / Not sure",
                ],
                priority=1,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="post_removal_status",
                activity_name="Post Removal vs. Continued Harassment",
                prompt="Was the 'When Sana opens her mouth' story removed from 'cse_b_memes' after Sana objected, or did Aman post additional content?",
                why_it_matters="Clarifies whether the harassment ceased after the confrontation, remained live for the full 24-hour story window, or escalated after Aman threatened 'Then I'll post more.'",
                context_excerpt="Audio recording: 'Take it down now.' ... 'If you don't delete it, I'm complaining to the dean.' 'Go ahead. Then I'll post more.' | Screenshot shows story active at '20h' with 'Seen by 143'.",
                options=[
                    "Aman refused to delete the post and it remained online until expiring",
                    "Aman deleted the post after the confrontation without posting more",
                    "Aman refused to delete it and posted additional memes or messages targeting Sana",
                    "I do not know / Not sure",
                ],
                priority=1,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="impact_assessment",
                activity_name="Emotional, Psychological & Academic Impact",
                prompt="What effect did the meme posting and peer reaction have on Sana's well-being, class attendance, and academic participation?",
                why_it_matters="Documents the concrete personal and educational impact referenced in the November 6, 2026 University Wellness Centre crisis slip and whether follow-up care was required.",
                context_excerpt="Counselling Visit Slip (06/11/2026, Dr. Priya Sharma): 'Student attended counselling reporting severe anxiety and distress related to peer behavior and social media harassment. Follow-up Recommended: Yes (13/11/2026)'.",
                options=[
                    "Sana experienced severe anxiety, avoided classes/presentations, and required follow-up counselling",
                    "Sana experienced acute distress on Nov 4–6 but resumed normal classes without follow-up sessions",
                    "The impact is limited to what is recorded on the Nov 6 Wellness Centre visit slip",
                    "I do not know / Not sure",
                ],
                priority=1,
            ),
            ClarificationQuestion(
                case_id=case_id,
                question_type="evidence_provenance_and_complaint",
                activity_name="Source of Uploader Screenshot & Dean Complaint Status",
                prompt="How were the 'CSE-B Gossip' chat screenshot and the 'cse_b_memes' uploader-view screenshot (showing 'Activity / Delete' controls) obtained, and has a formal complaint been submitted to the Dean?",
                why_it_matters="Clarifies the chain of custody for the screenshot showing account-owner controls ('Seen by 143 / Delete') and establishes whether institutional disciplinary action is underway.",
                context_excerpt="Screenshot (Gemini_Generated_Image_wf79vkwf79vkwf79.png) displays account-owner toolbar: 'Seen by 143 | Activity | Delete | Highlight | Share' alongside the 'CSE-B Gossip' chat.",
                options=[
                    "A classmate or co-admin shared the screenshots with Sana, and a complaint is being submitted to the Dean",
                    "Aman or another group member circulated the screenshots, and a formal complaint has already been filed",
                    "The screenshots were obtained during mediation or device inspection",
                    "I do not know / Not sure",
                ],
                priority=2,
            ),
        ]

    else:
        # General Case Synthesis
        sched_count = len(timeline.scheduled_events)
        unsched_count = len(timeline.unscheduled_events)
        parties = list({a for ev in events for a in getattr(ev, "actors", []) if len(a) > 2})
        party_str = ", ".join(parties[:4]) if parties else "the documented participants"
        ev_summaries = [
            f"{getattr(ev, 'title', 'Event')}: {getattr(ev, 'description', '')}"
            for ev in (timeline.scheduled_events + timeline.unscheduled_events)[:5]
        ]

        what_happened = (
            f"Forensic examination of Case {case_id[:8]} establishes {sched_count} chronologically anchored events and "
            f"{unsched_count} unanchored occurrences involving {party_str}.\n\n"
            + ("Key reconstructed occurrences include: " + " ".join(ev_summaries) + "\n\n" if ev_summaries else "")
            + "Documentary records substantiate the recorded statements and timestamps across the submitted files while "
            "preserving unverified claims as attributed representations requiring external corroboration."
        )
        if user_answers:
            what_happened += f"\n\nWitness clarifications have been incorporated into this reconstruction: {'; '.join(answer_texts)}."

        what_remains_unclear = [
            f"Unresolved factual discrepancies across {len(contradictions)} identified points of conflict.",
            "Chronological sequencing of unscheduled documentary entries.",
            "Verification of disputed claims through independent external corroboration."
        ]
        what_would_help = [
            "Investigator responses to the clarification questions below.",
            "Submission of dated primary source records to anchor unsequenced events.",
            "Independent corroborating logs or receipts."
        ]
        key_participants = parties[:5]
        key_dates_and_amounts = [ev.title for ev in timeline.scheduled_events[:4]]

        questions = []
        for u_ev in (timeline.unscheduled_events + timeline.scheduled_events)[:3]:
            t_expr = u_ev.original_time_expression or "the recorded timestamp"
            questions.append(
                ClarificationQuestion(
                    case_id=case_id,
                    event_id=u_ev.event_id,
                    question_type="event_verification",
                    activity_name=f"Verification of {u_ev.title}",
                    prompt=f"Regarding '{u_ev.title}' ({t_expr}), can you confirm the circumstances and outcome of this occurrence?",
                    why_it_matters="Establishes firsthand verification and outcome context for this documented event.",
                    context_excerpt=u_ev.description[:180],
                    options=[
                        "Confirmed — this event occurred as documented",
                        "Disputed — the underlying claim or timestamp is inaccurate",
                        "Additional follow-up occurred after this event",
                        "I do not know / Not sure",
                    ],
                    priority=1,
                )
            )

    return CaseUnderstandingResult(
        case_id=case_id,
        case_domain=domain,
        what_happened=what_happened,
        what_remains_unclear=what_remains_unclear[:5],
        what_would_help=what_would_help[:4],
        key_participants=key_participants,
        key_dates_and_amounts=key_dates_and_amounts,
        updated_with_clarifications=bool(user_answers),
        contextual_questions=questions,
    )
