# Evidence AI — Development Progress & Strategic Roadmap

**Project Phase:** Multi-Modal Forensic Extraction & Entity Disambiguation MVP  
**Current Assessment:** **95% Complete (MVP Scope)**  
**Audit Date:** November 14, 2026  

---

## 1. Executive MVP Progress Assessment

| Milestone Area | Status | Verified Capabilities | Outstanding Gap |
| :--- | :---: | :--- | :--- |
| **Forensic Storage & Hashing** | **100%** | SHA-256 fingerprinting, immutable storage paths, append-only SQLite `audit_log` | None |
| **Multi-Modal Extraction** | **100%** | PaddleOCR PP-OCRv6, Faster-Whisper Small INT8, python-docx, hybrid PDF, JSON, CSV, EML, TXT | None |
| **Data Normalization** | **100%** | Pydantic v2 `NormalizedExtractionRecord`, source location tracking (page, line, time, sender) | None |
| **Entity Intelligence (GLiNER)** | **100%** | Pretrained `urchade/gliner_small-v2.1` with offline caching and email/phone/IP regex supplements | None |
| **Cross-Evidence Matching (RapidFuzz)**| **100%** | `token_sort_ratio` candidate clustering without auto-merging | None |
| **Human Review Workflow** | **100%** | Confirm, Separate, Reject, Undo with SQLite persistence and forensic audit logging | None |
| **Event Extraction & Modality** | **100%** | Grounded Qwen 2.5 structured extraction; modality classification (plans != completed events) | None |
| **Deterministic Timeline** | **100%** | Chronological ordering of anchored events; unscheduled/ambiguous times safely segregated | None |
| **Contradiction Reasoning** | **100%** | Cross-evidence time discrepancy and plan vs execution contradiction detection | None |
| **Clarification Quiz Engine** | **100%** | Targeted non-leading questionnaires with self-reported ordinal surety (0-4) | None |
| **Forensic Incident Reporting** | **100%** | Comprehensive neutral report synthesis with SHA-256 custody tables and printable HTML | None |
| **Frontend UI Integration** | **100%** | 6-tab navigation (Evidence, Entities, Events, Timeline, Quiz, Report) with live reactivity | None |

---

## 2. Recommended Next 5 Development Tasks

### Task 1: Asynchronous Task Queue for Heavy Multi-File Ingestion
- **Priority:** **HIGH**
- **Rationale:** Currently, multi-file uploads execute extraction synchronously within the HTTP request cycle. While fast for individual documents (<200ms) and screenshots (~1.8s), batch uploading 20+ large audio or multi-page scanned PDF files can block the HTTP connection.
- **Affected Modules:**
  - `backend/routes.py`: Convert batch extraction endpoints to return HTTP 202 Accepted with a task ID.
  - `backend/tasks.py` (New): Worker process or background task executor (using FastAPI `BackgroundTasks` or Celery/Redis).
  - `frontend/src/pages/CaseDetails.tsx`: Poll task status or use WebSocket for real-time progress indicators.
- **Verification:** Upload 10 audio files simultaneously; verify HTTP response returns in <500ms and files transition to "Extracted" as jobs complete in the background.

---

### Task 2: Court-Admissible Forensic Case Dossier Export (PDF / JSON)
- **Priority:** **HIGH**
- **Rationale:** Forensic investigators must produce verifiable evidence reports for prosecutors, judges, or defense counsel containing chain-of-custody metadata, cryptographic hashes, verified entity linkages, and reviewer audit signatures.
- **Affected Modules:**
  - `backend/reporting.py` (New): Generates a standardized PDF dossier (via ReportLab or WeasyPrint) and JSON forensic manifest.
  - `backend/routes.py`: Add `GET /api/cases/{case_id}/export`.
  - `frontend/src/pages/CaseDetails.tsx`: Add "Export Case Dossier" button in header.
- **Verification:** Trigger case export; verify generated PDF contains case summary, evidence table with bit-accurate SHA-256 hashes, confirmed entities, and full audit log history.

---

### Task 3: Interactive Audio Waveform Player with Segment Scrubbing
- **Priority:** **MEDIUM**
- **Rationale:** Faster-Whisper generates granular segment timestamps (`start`, `end`, `text`). Presenting these alongside an interactive audio waveform allows investigators to click any transcript segment and immediately listen to the corresponding audio timestamp.
- **Affected Modules:**
  - `frontend/package.json`: Add `wavesurfer.js`.
  - `frontend/src/components/audio/AudioWaveformPlayer.tsx` (New): Waveform renderer with click-to-scrub functionality.
  - `frontend/src/pages/CaseDetails.tsx`: Embed waveform player in evidence drawer for audio files.
- **Verification:** Open an audio file in the inspection modal; click a segment timestamp and confirm audio playback jumps to the exact second.

---

### Task 4: Interactive Entity Relationship Graph Visualization
- **Priority:** **MEDIUM**
- **Rationale:** Viewing cross-evidence entities in a relational graph allows investigators to spot hidden connections between persons of interest, bank accounts, and phone numbers that span multiple cases.
- **Affected Modules:**
  - `frontend/package.json`: Add `@xyflow/react` (React Flow) or `cytoscape`.
  - `frontend/src/components/intelligence/EntityGraphView.tsx` (New): Node-edge graph component.
  - `frontend/src/pages/CaseDetails.tsx`: Add "Graph View" sub-tab in Entity Intelligence section.
- **Verification:** Generate candidate matches; verify nodes represent confirmed/pending entities and edges represent co-occurrence in evidence files.

---

### Task 5: Scanned PDF Resolution Preprocessing & Deskew Pipeline
- **Priority:** **LOW**
- **Rationale:** Low-quality smartphone scans of physical documents frequently have skew, perspective distortion, or shadow artifacts that degrade OCR accuracy.
- **Affected Modules:**
  - `src/extraction/pdf_extractor.py`: Add OpenCV (`cv2`) preprocessing: Otsu binarization, Hough transform deskewing, and unsharp masking before dispatching bitmap to PaddleOCR.
- **Verification:** Test on rotated 15-degree scanned receipt; confirm OCR accuracy improves by >15%.
