import { Case, EvidenceFile, ActivityRecord } from '../types';

// Helper to generate a minimal audible WAV base64 string for demo audio playback
function createBeepWavDataUrl(freq = 440, duration = 3): string {
  const sampleRate = 8000;
  const numSamples = sampleRate * duration;
  const buffer = new ArrayBuffer(44 + numSamples);
  const view = new DataView(buffer);

  // RIFF identifier
  view.setUint32(0, 0x52494646, false); // "RIFF"
  view.setUint32(4, 36 + numSamples, true);
  view.setUint32(8, 0x57415645, false); // "WAVE"
  // fmt subchunk
  view.setUint32(12, 0x666d7420, false); // "fmt "
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate, true);
  view.setUint16(32, 1, true);
  view.setUint16(34, 8, true);
  // data subchunk
  view.setUint32(36, 0x64617461, false); // "data"
  view.setUint32(40, numSamples, true);

  // Write sine wave samples
  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;
    const val = Math.floor(128 + 100 * Math.sin(2 * Math.PI * freq * t) * Math.exp(-t * 0.3));
    view.setUint8(44 + i, Math.min(255, Math.max(0, val)));
  }

  // Convert to base64
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return 'data:audio/wav;base64,' + btoa(binary);
}

export const INITIAL_CASES: Case[] = [
  {
    id: 'CASE-2026-081',
    title: 'Workplace Harassment & Targeted Defamation',
    description: 'Collection of persistent threatening emails, WhatsApp message screenshots, and recorded voice notes from executive accounts.',
    status: 'Active',
    priority: 'Critical',
    createdAt: '2026-11-01T09:30:00Z',
    updatedAt: '2026-11-13T16:45:00Z',
    tags: ['Harassment', 'Executive', 'High Priority'],
    notes: [
      {
        id: 'note-1',
        caseId: 'CASE-2026-081',
        title: 'Initial Intake Conference',
        content: 'Client reports repeated unauthorized logins and intimidating voicemails received between 21:00 and 02:00. Advised client to preserve all original message exports without modification.',
        createdAt: '2026-11-01T11:00:00Z',
        updatedAt: '2026-11-01T11:00:00Z',
      },
      {
        id: 'note-2',
        caseId: 'CASE-2026-081',
        title: 'Chain-of-Custody Verification',
        content: 'All screenshots verified against native iOS camera roll timestamps. Digital SHA-256 fingerprints recorded for court submission.',
        createdAt: '2026-11-05T14:15:00Z',
        updatedAt: '2026-11-05T14:15:00Z',
      }
    ]
  },
  {
    id: 'CASE-2026-094',
    title: 'Financial Embezzlement & Wire Fraud Inquiry',
    description: 'Altered vendor invoices, falsified bank transfer confirmations, and Slack export threads indicating deliberate dual-ledger routing.',
    status: 'Under Review',
    priority: 'High',
    createdAt: '2026-11-06T13:20:00Z',
    updatedAt: '2026-11-12T11:10:00Z',
    tags: ['Fraud', 'Financial', 'Corporate'],
    notes: [
      {
        id: 'note-3',
        caseId: 'CASE-2026-094',
        title: 'Forensic Audit Initial Findings',
        content: 'Cross-referenced PDF invoice vendor registration against public corporate registry. Signatures and wire routing numbers do not reconcile.',
        createdAt: '2026-11-07T10:00:00Z',
        updatedAt: '2026-11-07T10:00:00Z',
      }
    ]
  },
  {
    id: 'CASE-2026-102',
    title: 'Intellectual Property Breach & Source Exfiltration',
    description: 'Unauthorized access to proprietary CAD schematics and source code repositories prior to senior staff departure.',
    status: 'Active',
    priority: 'Medium',
    createdAt: '2026-11-09T08:00:00Z',
    updatedAt: '2026-11-14T10:30:00Z',
    tags: ['IP Theft', 'Access Logs'],
    notes: [
      {
        id: 'note-4',
        caseId: 'CASE-2026-102',
        title: 'USB Device Access Logs',
        content: 'Correlated git checkout logs with Windows Event Viewer USB mounting records at 03:22 AM on workstation WS-402.',
        createdAt: '2026-11-10T16:20:00Z',
        updatedAt: '2026-11-10T16:20:00Z',
      }
    ]
  }
];

export const INITIAL_EVIDENCE: EvidenceFile[] = [
  // 4 Screenshots / Images
  {
    id: 'EVD-IMG-001',
    caseId: 'CASE-2026-081',
    fileName: 'whatsapp_intimidation_thread.png',
    displayName: 'WhatsApp Threat Message Screenshot',
    fileType: 'image',
    fileExtension: 'png',
    fileSize: 1845200, // ~1.8 MB
    dateAdded: '2026-11-02T10:14:22Z',
    notes: 'Threatening direct message sent from phone number +1 (555) 019-2834 threatening retaliation if police contacted.',
    metadata: {
      sha256: '9f83c07629b3a7b6cf21c7d23d8544e3f140679b3c3757a2f58869ff59c11867',
      resolution: '1170x2532',
      mimeType: 'image/png',
      authenticityStatus: 'Verified',
      authorOrSource: 'Apple iPhone 14 Pro Screen Capture'
    },
    previewUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=900&q=80'
  },
  {
    id: 'EVD-IMG-002',
    caseId: 'CASE-2026-081',
    fileName: 'telegram_secret_chat_delete_timer.jpg',
    displayName: 'Self-Destructing Telegram Chat Capture',
    fileType: 'image',
    fileExtension: 'jpg',
    fileSize: 924300,
    dateAdded: '2026-11-03T18:40:10Z',
    notes: 'Photographed using secondary device before 30-second self-destruct timer expired.',
    metadata: {
      sha256: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
      resolution: '3024x4032',
      mimeType: 'image/jpeg',
      authenticityStatus: 'Verified',
      authorOrSource: 'Google Pixel 8 Camera'
    },
    previewUrl: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=900&q=80'
  },
  {
    id: 'EVD-IMG-003',
    caseId: 'CASE-2026-094',
    fileName: 'altered_invoice_vendor_stamp.png',
    displayName: 'Dual-Stamped Altered Vendor Invoice',
    fileType: 'image',
    fileExtension: 'png',
    fileSize: 2410800,
    dateAdded: '2026-11-08T12:05:44Z',
    notes: 'High-res flatbed scan highlighting mismatched font kerning and forged accounting stamp in footer.',
    metadata: {
      sha256: 'a12f3bcde9098172635441829038475610293847561029384756102938475610',
      resolution: '2480x3508',
      mimeType: 'image/png',
      authenticityStatus: 'Verified',
      authorOrSource: 'Fujitsu ScanSnap iX1600'
    },
    previewUrl: 'https://images.unsplash.com/photo-1586281380349-632531db7ed4?auto=format&fit=crop&w=900&q=80'
  },
  {
    id: 'EVD-IMG-004',
    caseId: 'CASE-2026-102',
    fileName: 'security_door_badge_access.webp',
    displayName: 'Server Room CCTV Frame Capture',
    fileType: 'image',
    fileExtension: 'webp',
    fileSize: 642100,
    dateAdded: '2026-11-11T04:15:30Z',
    notes: 'Surveillance still showing badge tap at 03:19:42 AM by badge ID #77291.',
    metadata: {
      sha256: '3819203948571029384756102938475610293847561029384756102938475610',
      resolution: '1920x1080',
      mimeType: 'image/webp',
      authenticityStatus: 'Verified',
      authorOrSource: 'Axis Communications Q1656-LE'
    },
    previewUrl: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=900&q=80'
  },

  // 3 Audio Recordings (playable demo sound)
  {
    id: 'EVD-AUD-001',
    caseId: 'CASE-2026-081',
    fileName: 'intimidating_voicemail_2340.mp3',
    displayName: 'Intimidating Midnight Voicemail',
    fileType: 'audio',
    fileExtension: 'mp3',
    fileSize: 3140500,
    dateAdded: '2026-11-04T02:15:00Z',
    notes: '42-second message left by caller warning against reporting internal accounting anomalies.',
    metadata: {
      sha256: '7c82361726354418290384756102938475610293847561029384756102938475',
      duration: '00:42',
      bitrate: '320 kbps',
      mimeType: 'audio/mpeg',
      authenticityStatus: 'Verified',
      authorOrSource: 'AT&T Visual Voicemail AMR-WB to MP3'
    },
    audioUrl: createBeepWavDataUrl(380, 4)
  },
  {
    id: 'EVD-AUD-002',
    caseId: 'CASE-2026-081',
    fileName: 'boardroom_confrontation_memo.wav',
    displayName: 'Recorded Executive Confrontation',
    fileType: 'audio',
    fileExtension: 'wav',
    fileSize: 12480000,
    dateAdded: '2026-11-05T19:30:00Z',
    notes: 'Single-party consent voice memo recorded during mandatory closed-door disciplinary session.',
    metadata: {
      sha256: '6172839401928374651029384756102938475610293847561029384756102938',
      duration: '03:15',
      bitrate: '1411 kbps',
      mimeType: 'audio/wav',
      authenticityStatus: 'Verified',
      authorOrSource: 'Apple Voice Memos Linear PCM'
    },
    audioUrl: createBeepWavDataUrl(520, 5)
  },
  {
    id: 'EVD-AUD-003',
    caseId: 'CASE-2026-094',
    fileName: 'cfo_wire_instruction_call.m4a',
    displayName: 'Recorded Wire Routing Call',
    fileType: 'audio',
    fileExtension: 'm4a',
    fileSize: 4890000,
    dateAdded: '2026-11-10T14:45:00Z',
    notes: 'Audio recording of call ordering immediate transfer override to offshore intermediary bank.',
    metadata: {
      sha256: '8392019283746510293847561029384756102938475610293847561029384756',
      duration: '01:58',
      bitrate: '256 kbps',
      mimeType: 'audio/x-m4a',
      authenticityStatus: 'Verified',
      authorOrSource: 'PBX Telecom Automated Archive'
    },
    audioUrl: createBeepWavDataUrl(440, 3)
  },

  // 2 Chat Exports
  {
    id: 'EVD-TXT-001',
    caseId: 'CASE-2026-081',
    fileName: 'signal_chat_export_verbatim.txt',
    displayName: 'Signal Secure Chat History Log',
    fileType: 'text',
    fileExtension: 'txt',
    fileSize: 45200,
    dateAdded: '2026-11-06T09:12:00Z',
    notes: 'Raw unedited decrypted chat export exported directly from Signal client version 7.21.',
    metadata: {
      sha256: '1029384756102938475610293847561029384756102938475610293847561029',
      mimeType: 'text/plain',
      authenticityStatus: 'Verified',
      authorOrSource: 'Signal Desktop Client'
    },
    textContent: `====================================================================
SIGNAL MESSAGING EXPORT — FORENSIC LOG
Target Handle: [REDACTED_DEFENDANT]
Recipient Handle: [VICTIM_CLIENT]
Export Timestamp: 2026-11-06 09:10:00 UTC
====================================================================

[2026-11-02 21:04:12 UTC] [REDACTED_DEFENDANT]:
If you bring up the Q3 reconciliation figures in tomorrow's executive review, consider your career terminated.

[2026-11-02 21:05:03 UTC] [VICTIM_CLIENT]:
The numbers show an unexplained $450,000 discrepancy routed through Apex Holdings. I am legally obligated to flag audit inconsistencies.

[2026-11-02 21:06:22 UTC] [REDACTED_DEFENDANT]:
You aren't obligated to do anything except follow company directives. We have your non-disclosure agreement on file. Do not force my hand.`
  },
  {
    id: 'EVD-TXT-002',
    caseId: 'CASE-2026-102',
    fileName: 'git_checkout_audit_trail.json',
    displayName: 'Bitbucket Git Access Logs JSON',
    fileType: 'text',
    fileExtension: 'json',
    fileSize: 128400,
    dateAdded: '2026-11-12T17:20:10Z',
    notes: 'Structured JSON log showing bulk clone of proprietary algorithms repo outside working hours.',
    metadata: {
      sha256: '3847561029384756102938475610293847561029384756102938475610293847',
      mimeType: 'application/json',
      authenticityStatus: 'Verified',
      authorOrSource: 'Atlassian Enterprise Audit Log'
    },
    textContent: JSON.stringify({
      audit_version: "2.4.1",
      event_type: "REPO_BULK_EXPORT",
      source_ip: "192.168.1.144",
      user_id: "usr_executive_departure",
      repository: "firmware/quantum-optical-core",
      branch: "main",
      commits_downloaded: 481,
      total_bytes_transferred: 849302194,
      timestamp: "2026-11-12T03:22:19.481Z",
      status: "COMPLETED"
    }, null, 2)
  },

  // 2 Email Records (.eml / .csv)
  {
    id: 'EVD-TXT-003',
    caseId: 'CASE-2026-081',
    fileName: 'hr_complaint_retaliation.eml',
    displayName: 'RFC-822 HR Retaliation Notice Email',
    fileType: 'text',
    fileExtension: 'eml',
    fileSize: 68100,
    dateAdded: '2026-11-07T11:45:00Z',
    notes: 'Complete RFC-822 email message with full DKIM, SPF, and DMARC passing headers.',
    metadata: {
      sha256: '5610293847561029384756102938475610293847561029384756102938475610',
      mimeType: 'message/rfc822',
      authenticityStatus: 'Verified',
      authorOrSource: 'Microsoft Exchange Online Mail Server'
    },
    textContent: `From: "Executive Director" <ed@acmecorp-internal.com>
To: "Victim Employee" <victim@acmecorp-internal.com>
Subject: Re: Notice of Formal Grievance Filing
Date: Tue, 07 Nov 2026 11:42:01 +0000
Message-ID: <CAB20261107.49102@acmecorp-internal.com>
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=acmecorp-internal.com; s=selector1;
Authentication-Results: spf=pass smtp.mailfrom=acmecorp-internal.com; dkim=pass

Your formal complaint has been received. Be advised that proceeding with this matter externally will trigger immediate civil action for breach of loyalty and immediate suspension without compensation.`
  },
  {
    id: 'EVD-TXT-004',
    caseId: 'CASE-2026-094',
    fileName: 'swift_transfer_records_export.csv',
    displayName: 'SWIFT International Wire Ledger CSV',
    fileType: 'text',
    fileExtension: 'csv',
    fileSize: 31200,
    dateAdded: '2026-11-09T15:10:00Z',
    notes: 'Parsed spreadsheet showing wire destinations matching offshore shell corporate accounts.',
    metadata: {
      sha256: '2938475610293847561029384756102938475610293847561029384756102938',
      mimeType: 'text/csv',
      authenticityStatus: 'Verified',
      authorOrSource: 'JPMorgan Chase Treasury Portal'
    },
    textContent: `Transaction_ID,Date,Origin_Account,Beneficiary_Name,Beneficiary_IBAN,Amount_USD,Authorized_By
TX-9841029,2026-11-01,984029104,Apex Offshore Global,CY28002001928401928401,450000.00,CFO_DIRECT
TX-9841030,2026-11-03,984029104,Apex Offshore Global,CY28002001928401928401,275000.00,CFO_DIRECT
TX-9841031,2026-11-06,984029104,Seashell Consulting LLC,PA91029384710293847102,185000.00,CFO_DIRECT`
  },

  // 2 Documents (.pdf, .docx)
  {
    id: 'EVD-DOC-001',
    caseId: 'CASE-2026-094',
    fileName: 'forensic_accounting_preliminary_audit.pdf',
    displayName: 'Preliminary Forensic Accounting Audit Report',
    fileType: 'document',
    fileExtension: 'pdf',
    fileSize: 4892000,
    dateAdded: '2026-11-11T13:00:00Z',
    notes: '28-page certified CPA forensic review identifying 3 unapproved wire authorizations.',
    metadata: {
      sha256: '7465102938475610293847561029384756102938475610293847561029384756',
      pageCount: 28,
      mimeType: 'application/pdf',
      authenticityStatus: 'Verified',
      authorOrSource: 'Deloitte Forensics & Dispute Services'
    }
  },
  {
    id: 'EVD-DOC-002',
    caseId: 'CASE-2026-102',
    fileName: 'non_compete_trade_secret_agreement.docx',
    displayName: 'Executed Non-Compete & IP Agreement',
    fileType: 'document',
    fileExtension: 'docx',
    fileSize: 1450000,
    dateAdded: '2026-11-13T09:30:00Z',
    notes: 'Signed counterparty agreement with intellectual property retention clauses.',
    metadata: {
      sha256: '9283746510293847561029384756102938475610293847561029384756102938',
      pageCount: 14,
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      authenticityStatus: 'Verified',
      authorOrSource: 'Corporate Legal Repository'
    }
  }
];

export const INITIAL_ACTIVITIES: ActivityRecord[] = [
  {
    id: 'act-1',
    caseId: 'CASE-2026-102',
    caseTitle: 'Intellectual Property Breach & Source Exfiltration',
    action: 'EVIDENCE_ADDED',
    evidenceName: 'non_compete_trade_secret_agreement.docx',
    description: 'Uploaded executed trade secret contract with SHA-256 validation.',
    timestamp: '2026-11-13T09:30:00Z'
  },
  {
    id: 'act-2',
    caseId: 'CASE-2026-094',
    caseTitle: 'Financial Embezzlement & Wire Fraud Inquiry',
    action: 'CASE_STATUS_CHANGED',
    description: 'Case status updated to "Under Review" pending forensic CPA audit.',
    timestamp: '2026-11-12T11:10:00Z'
  },
  {
    id: 'act-3',
    caseId: 'CASE-2026-081',
    caseTitle: 'Workplace Harassment & Targeted Defamation',
    action: 'NOTE_ADDED',
    description: 'Added case note: "Chain-of-Custody Verification".',
    timestamp: '2026-11-05T14:15:00Z'
  },
  {
    id: 'act-4',
    caseId: 'CASE-2026-081',
    caseTitle: 'Workplace Harassment & Targeted Defamation',
    action: 'EVIDENCE_ADDED',
    evidenceName: 'whatsapp_intimidation_thread.png',
    description: 'Uploaded WhatsApp threatening message screenshot with SHA-256 fingerprint.',
    timestamp: '2026-11-02T10:14:22Z'
  },
  {
    id: 'act-5',
    caseId: 'CASE-2026-081',
    caseTitle: 'Workplace Harassment & Targeted Defamation',
    action: 'CASE_CREATED',
    description: 'Created case "Workplace Harassment & Targeted Defamation" [CASE-2026-081].',
    timestamp: '2026-11-01T09:30:00Z'
  }
];
