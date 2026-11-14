# Evidence AI — Intake & Forensic Preservation Platform

> **Victim-First Digital Evidence Platform (24-Hour Hackathon MVP)**  
> Securely ingest, cryptographically fingerprint (SHA-256), and forensically preserve digital evidence (images, audio, and chat/email text logs) with strict local privacy.

---

## 🛡️ Key Features

1. **Victim-First & Local-First Privacy**:
   - Zero third-party cloud data leakage: original files are preserved untouched in `./storage/originals/{case_id}/`.
   - Clear privacy guarantee: *"Files are stored locally and never sent to third parties."*
2. **Three Categorized Intake Zones**:
   - **Images**: `.png`, `.jpg`, `.jpeg`, `.webp` (with thumbnail preview).
   - **Audio Recordings**: `.mp3`, `.wav`, `.m4a`, `.ogg`.
   - **Text & Exports**: `.txt`, `.json`, `.csv`, `.eml`, `.pdf` (WhatsApp/Signal chats, email logs).
3. **Forensic Integrity & Audit Trail**:
   - SHA-256 cryptographic hash calculated on raw bytes at upload time.
   - Append-only `audit_log` table tracking every upload action and metadata.
   - Court-admissible preservation: files stored unmodified using UUID filenames, retaining original filenames in the database.
4. **Authenticity Gate (Pluggable)**:
   - Built-in placeholder `run_authenticity_gate(file_path, file_type)` ready for deepfake / AI-generation detection models.
5. **Interactive UI**:
   - Auto-generated Case UUIDs with manual Case ID switching.
   - Drag-and-drop and click-to-browse file selection with multi-file support.
   - Per-file context notes, real-time progress bars, and status badges (`Ready`, `Uploading`, `Saved`, `Failed`).
   - One-click SHA-256 hash copying with instant visual confirmation.
   - Direct file download/viewing streaming from disk.

---

## 📁 Project Structure

```text
EvidenceAI_CodeY/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization & CORS configuration
│   ├── models.py            # SQLAlchemy models (cases, evidence, audit_log) & Pydantic schemas
│   ├── db.py                # Isolated SQLite database engine & session dependency
│   ├── routes.py            # Upload, retrieval, file streaming & validation endpoints
│   └── authenticity.py      # Pluggable authenticity & fake-detection gate
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React single-page intake application
│   │   ├── App.css          # Calm, accessible light theme styling
│   │   ├── index.css        # Minimal CSS resets
│   │   └── main.jsx         # Vite React entry point
│   ├── index.html           # HTML template with Inter typography
│   ├── package.json         # Frontend npm dependencies (React 18 + Vite 5)
│   └── vite.config.js       # Vite build & local dev server proxy
├── storage/
│   └── originals/           # Untouched evidence files organized by case ID
├── evidence_ai.db           # SQLite database
├── test_intake.py           # Automated end-to-end verification script
├── test_validation.py       # Validation boundary test script
├── requirements.txt         # Python dependencies
├── package.json             # Root npm helper scripts
└── README.md                # Project documentation & instructions
```

---

## 🗄️ Database Schema

The database layer is isolated in `backend/db.py` and uses SQLite via SQLAlchemy (can be switched to PostgreSQL by setting the `DATABASE_URL` environment variable).

### 1. `cases`
- `id` (String UUID, Primary Key): Unique incident case identifier.
- `created_at` (DateTime): Case creation timestamp.

### 2. `evidence`
- `id` (String UUID, Primary Key): Unique evidence identifier.
- `case_id` (String UUID, Foreign Key): Associated case.
- `original_filename` (String): Original name of uploaded file.
- `stored_path` (String): Path to untouched file in `storage/originals/{case_id}/`.
- `file_type` (String): Category (`image` | `audio` | `text`).
- `mime_type` (String): Validated MIME type.
- `size_bytes` (Integer): File size in bytes.
- `sha256` (String): 64-character cryptographic SHA-256 fingerprint.
- `notes` (Text, Nullable): User context notes (e.g. "WhatsApp screenshot from 12 March").
- `authenticity_passed` (Boolean): Result of authenticity gate.
- `authenticity_score` (Float, Nullable): Detection score / confidence.
- `uploaded_at` (DateTime): Timestamp of upload.

### 3. `audit_log` (Append-Only)
- `id` (String UUID, Primary Key): Log identifier.
- `case_id` (String UUID): Associated case.
- `evidence_id` (String UUID, Nullable): Target evidence item.
- `action` (String): Action performed (`UPLOADED`).
- `timestamp` (DateTime): Log entry timestamp.
- `details` (Text / JSON): Forensic record payload including SHA-256 and metadata.

---

## 🚀 Getting Started

### Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+ or 20+

---

### Step 1: Install Dependencies

#### Backend (Python)
From the project root:
```bash
pip install -r requirements.txt
```

#### Frontend (Node / React)
From the `frontend/` directory (or use root helper):
```bash
cd frontend
npm install
cd ..
```

---

### Step 2: Run the Application

#### Terminal 1 — Start Backend Server (FastAPI)
From the project root:
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs (Swagger UI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

#### Terminal 2 — Start Frontend Server (React + Vite)
From the project root:
```bash
cd frontend
npm run dev
```
- Open the application in your browser: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Automated Verification Test

An end-to-end verification script is provided to test the entire intake workflow:
```bash
python test_intake.py
```

This script:
1. Generates test evidence of each category (`.png`, `.mp3`, `.txt`).
2. Uploads all 3 files via `POST /api/cases/{case_id}/evidence` with individual notes.
3. Retrieves records via `GET /api/cases/{case_id}/evidence`.
4. Streams back each file via `GET /api/evidence/{id}/file` and verifies SHA-256 byte-for-byte.
5. Inspects `evidence_ai.db` to confirm `cases`, `evidence`, and `audit_log` entries are recorded.
6. Verifies files are stored untouched in `storage/originals/{case_id}/`.

To test rejection of invalid file extensions or payloads:
```bash
python test_validation.py
```

---

## 🔌 Authenticity Gate Placeholder

The file `backend/authenticity.py` exposes:
```python
def run_authenticity_gate(file_path: str, file_type: str) -> dict:
    return {"passed": True, "score": None}
```
This is called on every upload and the result is committed to the database. Plug in your fake-detection, EXIF analysis, or synthetic audio models here when ready.

---

## 🔒 Privacy & Forensic Integrity

- **Originals Untouched**: Files are written as binary streams directly to disk without alteration or re-compression.
- **Deterministic Hashes**: SHA-256 is computed before storing and validated against streamed downloads.
- **Append-Only Ledger**: The audit log has no update or delete endpoints to ensure chain of custody.
