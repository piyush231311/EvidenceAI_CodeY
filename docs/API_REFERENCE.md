# Evidence AI — REST API Reference & Endpoint Inventory

**API Version:** 1.0.0  
**Host URL:** `http://127.0.0.1:8000`  
**Swagger UI:** `http://127.0.0.1:8000/docs`  
**OpenAPI Spec:** `http://127.0.0.1:8000/openapi.json`  
**Audit Date:** November 14, 2026  

---

## 1. Network & Reverse Proxy Architecture

The frontend communicates with the backend via Vite's built-in development reverse proxy configured in [`frontend/vite.config.js`](file:///c:/project/frontend/vite.config.js):

```javascript
server: {
  port: 5173,
  host: '127.0.0.1',
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      secure: false
    }
  }
}
```

Any client request in `frontend/src/services/api.ts` dispatched to `/api/*` is transparently forwarded to `http://127.0.0.1:8000/api/*`, eliminating browser CORS issues in local development.

---

## 2. Complete REST API Endpoint Inventory

| # | Method | Route | Purpose | Request Format | Response Format | Python Handler | Frontend Caller | Verification Status |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :-: |
| **1** | `GET` | `/api/health` | Service health check | None | `{"status": "healthy", "service": "..."}` | `backend/main.py:health_check` | TopNavbar status dot | **VERIFIED** (HTTP 200) |
| **2** | `GET` | `/api/cases` | List all cases | None | `List[CaseResponse]` | `backend/routes.py:list_cases` | `api.getCases()` in `Cases.tsx` | **VERIFIED** (HTTP 200) |
| **3** | `POST` | `/api/cases` | Create or initialize case | `{"id": "optional-custom-id"}` | `CaseResponse` | `backend/routes.py:create_case` | `api.createCase()` in `Cases.tsx` | **VERIFIED** (HTTP 201) |
| **4** | `DELETE` | `/api/cases/{case_id}` | Delete case & all files | URL Path Param `case_id` | HTTP 204 No Content | `backend/routes.py:delete_case` | `api.deleteCase()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 204) |
| **5** | `POST` | `/api/cases/{case_id}/evidence` | Intake & upload evidence | `multipart/form-data`: `files`, `notes`, `notes_map` | `List[EvidenceResponse]` | `backend/routes.py:upload_evidence` | `api.uploadEvidence()` in `UploadEvidence.tsx` | **VERIFIED** (HTTP 201) |
| **6** | `GET` | `/api/cases/{case_id}/evidence` | Get all evidence for case | URL Path Param `case_id` | `List[EvidenceResponse]` | `backend/routes.py:get_case_evidence` | `api.getCaseEvidence()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **7** | `GET` | `/api/evidence` | List all evidence across cases | None | `List[EvidenceResponse]` | `backend/routes.py:list_all_evidence` | `api.getAllEvidence()` in `EvidenceVault.tsx` | **VERIFIED** (HTTP 200) |
| **8** | `DELETE` | `/api/evidence/{evidence_id}` | Delete evidence record | URL Path Param `evidence_id` | HTTP 204 No Content | `backend/routes.py:delete_evidence` | `api.deleteEvidence()` in `EvidenceVault.tsx` | **VERIFIED** (HTTP 204) |
| **9** | `GET` | `/api/evidence/{evidence_id}/file` | Download original binary | URL Path Param `evidence_id` | Binary File Stream (`FileResponse`) | `backend/routes.py:download_evidence_file` | `api.getFileUrl()` direct download links | **VERIFIED** (HTTP 200) |
| **10** | `POST` | `/api/evidence/{evidence_id}/extract` | Re-run extraction on single file | URL Path Param `evidence_id` | `EvidenceResponse` | `backend/routes.py:trigger_evidence_extraction` | `api.triggerExtraction()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **11** | `POST` | `/api/cases/{case_id}/extract-all` | Batch extract all case evidence | URL Path Param `case_id` | `List[EvidenceResponse]` | `backend/routes.py:extract_all_case_evidence` | `api.extractAllCaseEvidence()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **12** | `POST` | `/api/cases/{case_id}/entities/match` | Run GLiNER + RapidFuzz clustering | URL Path Param `case_id` | `List[CandidateMatchResponse]` | `backend/routes.py:run_case_entity_matching` | `api.matchCaseEntities()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **13** | `GET` | `/api/cases/{case_id}/entities` | Retrieve stored candidate matches | URL Path Param `case_id` | `List[CandidateMatchResponse]` | `backend/routes.py:get_case_entities` | `api.getCaseEntities()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **14** | `POST` | `/api/entities/matches/{match_id}/review` | Submit human review action | `{"action": "confirm"\|"reject"\|"separate"\|"undo", "review_notes": "..."}` | `CandidateMatchResponse` | `backend/routes.py:review_entity_match` | `api.reviewEntityMatch()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **15** | `GET` | `/api/cases/{case_id}/audit-logs` | Retrieve forensic audit trail | URL Path Param `case_id` | `List[AuditLogResponse]` | `backend/routes.py:get_case_audit_logs` | Settings / Forensic review | **VERIFIED** (HTTP 200) |
| **16** | `GET` | `/api/system/ollama` | Check Ollama and Qwen status | None | `{"available": bool, "base_url": str, "configured_model": str, "model_present": bool}` | `backend/routes.py:check_ollama` | Backend System Diagnostic | **VERIFIED** (HTTP 200) |
| **17** | `POST` | `/api/cases/{case_id}/events/extract` | Extract structured events | URL Path Param `case_id` | `List[EventCandidateResponse]` | `backend/routes.py:extract_case_events` | `api.extractCaseEvents()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **18** | `GET` | `/api/cases/{case_id}/events` | Retrieve stored events | URL Path Param `case_id` | `List[EventCandidateResponse]` | `backend/routes.py:get_case_events` | `api.getCaseEvents()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **19** | `GET` | `/api/cases/{case_id}/timeline` | Reconstructed chronological timeline | URL Path Param `case_id` | `TimelineResponse` | `backend/routes.py:get_case_timeline` | `api.getCaseTimeline()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **20** | `GET` | `/api/cases/{case_id}/contradictions` | Detected cross-evidence conflicts | URL Path Param `case_id` | `List[ContradictionResponse]` | `backend/routes.py:get_case_contradictions` | `api.getCaseContradictions()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **21** | `POST` | `/api/cases/{case_id}/quiz/generate` | Generate targeted clarification quiz | URL Path Param `case_id` | `List[ClarificationQuestionResponse]` | `backend/routes.py:generate_case_quiz` | `api.generateClarificationQuiz()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **22** | `GET` | `/api/cases/{case_id}/quiz` | Retrieve active questionnaire | URL Path Param `case_id` | `List[ClarificationQuestionResponse]` | `backend/routes.py:get_case_quiz` | `api.getClarificationQuiz()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **23** | `POST` | `/api/cases/{case_id}/quiz/answers` | Submit clarification with surety | `{"question_id": "...", "selected_option": "...", "user_surety": "Very sure", "knowledge_basis": "..."}` | `UserAnswerResponse` | `backend/routes.py:submit_quiz_answer` | `api.submitQuizAnswer()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **24** | `POST` | `/api/cases/{case_id}/reconstruct` | Re-run timeline reconstruction | URL Path Param `case_id` | `{"timeline": ..., "contradictions": ...}` | `backend/routes.py:trigger_reconstruction` | `api.triggerReconstruction()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **25** | `POST` | `/api/cases/{case_id}/report/generate` | Synthesize forensic incident report | URL Path Param `case_id` | `ReportResponse` | `backend/routes.py:generate_incident_report` | `api.generateReport()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **26** | `GET` | `/api/cases/{case_id}/report` | Retrieve forensic report data | URL Path Param `case_id` | `ReportResponse` | `backend/routes.py:get_incident_report` | `api.getReport()` in `CaseDetails.tsx` | **VERIFIED** (HTTP 200) |
| **27** | `GET` | `/api/cases/{case_id}/report/html` | View/print full forensic HTML | URL Path Param `case_id` | `HTMLResponse (text/html)` | `backend/routes.py:get_incident_report_html` | `api.getReportHtmlUrl()` | **VERIFIED** (HTTP 200) |

---

## 3. Data Transfer Schemas

### `EvidenceResponse`
```json
{
  "id": "8e93ba1b-6cef-4a07-af1c-17f40ca8282e",
  "case_id": "CASE-2026-OMEGA",
  "original_filename": "invoice_9942.png",
  "stored_path": "storage/originals/CASE-2026-OMEGA/8e93ba1b.png",
  "file_type": "image",
  "mime_type": "image/png",
  "size_bytes": 104230,
  "sha256": "4af9b8033521b7640fdce24e2ecf75e003a27e7d69b35bc407c6f05f57ea6153",
  "notes": "Intake note from investigator",
  "authenticity_passed": true,
  "authenticity_score": 1.0,
  "uploaded_at": "2026-11-14T11:04:15.123456",
  "extracted_text": "OFFICIAL INVOICE #9942 TOTAL AMOUNT $45,000",
  "extraction_confidence": 0.9768,
  "extraction_metadata": "{\"engine\": \"PaddleOCR PP-OCRv6_small\", \"lines_count\": 1}",
  "processing_time_ms": 183.4
}
```

### `CandidateMatchResponse`
```json
{
  "id": "cand-9a0de78b-5985-4f63-b791-4c7c160bf94d",
  "case_id": "CASE-2026-OMEGA",
  "entity_type": "person",
  "canonical_name": "Marcus Vance",
  "similarity_score": 98.6,
  "status": "pending",
  "mentions": [
    {
      "text": "Marcus Vance",
      "evidence_id": "8e93ba1b-6cef-4a07-af1c-17f40ca8282e",
      "filename": "intelligence_report.docx",
      "confidence": 0.985,
      "start_char": 23,
      "end_char": 35
    },
    {
      "text": "Marcus Vance",
      "evidence_id": "9b12a31c-8cef-4a07-af1c-17f40ca8282e",
      "filename": "chat_export.json",
      "confidence": 0.990,
      "start_char": 10,
      "end_char": 22
    }
  ],
  "created_at": "2026-11-14T11:04:20.123456",
  "reviewed_at": null,
  "review_notes": null
}
```

### `ReviewMatchPayload`
```json
{
  "action": "confirm",
  "review_notes": "Forensically confirmed same target"
}
```
*Valid `action` values:* `"confirm"`, `"reject"`, `"separate"`, `"undo"`.

---

## 4. Standard Error Format

All error responses strictly follow the standard RFC 7807 problem details convention:

```json
{
  "detail": "Unsupported file type '.exe' for 'malware.exe'. Allowed extensions: .csv, .docx, .eml, .jpeg, .jpg, .json, .m4a, .mp3, .ogg, .pdf, .png, .txt, .wav, .webp"
}
```

- **HTTP 400 Bad Request:** Disallowed extension, MIME type mismatch, or invalid review action.
- **HTTP 404 Not Found:** Specified case ID or evidence ID does not exist in SQLite.
- **HTTP 413 Payload Too Large:** File size exceeds 50 MB threshold.
