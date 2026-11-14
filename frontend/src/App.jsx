import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

// Configuration for upload zones
const ZONES = [
  {
    key: 'image',
    title: 'Visual Evidence (Images)',
    subtitle: 'Screenshots, photos, scanned photos, threats',
    extensions: ['.png', '.jpg', '.jpeg', '.webp'],
    accept: 'image/png,image/jpeg,image/webp',
    icon: (
      <svg className="zone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
    ),
  },
  {
    key: 'audio',
    title: 'Audio Recordings',
    subtitle: 'Voicemails, calls, voice memos, ambient sound',
    extensions: ['.mp3', '.wav', '.m4a', '.ogg'],
    accept: 'audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/m4a,audio/x-m4a,audio/mp4,audio/ogg',
    icon: (
      <svg className="zone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
    ),
  },
  {
    key: 'text',
    title: 'Text & Export Logs',
    subtitle: 'WhatsApp/Signal exports, emails, PDFs, JSON logs',
    extensions: ['.txt', '.json', '.csv', '.eml', '.pdf'],
    accept: '.txt,.json,.csv,.eml,.pdf,text/plain,application/json,text/csv,application/pdf,message/rfc822',
    icon: (
      <svg className="zone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
    ),
  },
];

const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export default function App() {
  const [caseId, setCaseId] = useState('');
  const [caseInput, setCaseInput] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [stagedFiles, setStagedFiles] = useState([]); // files queued to upload
  const [evidenceList, setEvidenceList] = useState([]);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [reExtractingId, setReExtractingId] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);
  const [dragActiveZone, setDragActiveZone] = useState(null);
  const [backendOffline, setBackendOffline] = useState(false);

  // Initialize Case ID on first load
  useEffect(() => {
    const initialCaseId = generateUUID();
    setCaseId(initialCaseId);
    setCaseInput(initialCaseId);
  }, []);

  // Fetch evidence records whenever active caseId changes
  useEffect(() => {
    if (caseId) {
      fetchEvidence(caseId);
    }
  }, [caseId]);

  const fetchEvidence = async (targetCaseId) => {
    setIsLoadingEvidence(true);
    try {
      const res = await fetch(`${API_BASE}/api/cases/${targetCaseId}/evidence`);
      if (res.ok) {
        const data = await res.json();
        setEvidenceList(data);
        setBackendOffline(false);
      } else {
        setEvidenceList([]);
        setBackendOffline(true);
      }
    } catch (err) {
      console.warn('Backend service connection error:', err);
      setEvidenceList([]);
      setBackendOffline(true);
    } finally {
      setIsLoadingEvidence(false);
    }
  };

  const handleApplyCaseId = () => {
    let target = caseInput.trim();
    if (!target) {
      target = generateUUID();
      setCaseInput(target);
    }
    setCaseId(target);
    setErrorMessage('');
    setSuccessMessage(`Switched to Case: ${target}`);
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  const handleNewCase = () => {
    const newId = generateUUID();
    setCaseInput(newId);
    setCaseId(newId);
    setStagedFiles([]);
    setErrorMessage('');
    setSuccessMessage(`New Case Generated: ${newId}`);
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  const toggleExpandRow = (id) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleReExtract = async (evidenceId) => {
    setReExtractingId(evidenceId);
    try {
      const res = await fetch(`${API_BASE}/api/evidence/${evidenceId}/extract`, {
        method: 'POST',
      });
      if (res.ok) {
        const updated = await res.json();
        setEvidenceList((prev) =>
          prev.map((item) => (item.id === evidenceId ? updated : item))
        );
        setSuccessMessage(`AI extraction updated for ${updated.original_filename}`);
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        setErrorMessage('Failed to recompute extraction.');
      }
    } catch (err) {
      setErrorMessage(`Error triggering extraction: ${err.message}`);
    } finally {
      setReExtractingId(null);
    }
  };

  // Client-side file validation
  const validateFile = (file, zoneKey) => {
    const zone = ZONES.find((z) => z.key === zoneKey);
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    // Size limit validation (50 MB)
    if (file.size > MAX_SIZE_BYTES) {
      return `File "${file.name}" exceeds the 50 MB limit (${formatBytes(file.size)}).`;
    }

    // Extension validation
    if (!zone.extensions.includes(ext)) {
      return `File "${file.name}" is not supported in the ${zone.title} zone. Allowed: ${zone.extensions.join(', ')}`;
    }

    return null;
  };

  // Stage files dropped or selected in a specific zone
  const handleFilesAdded = (filesArray, zoneKey) => {
    setErrorMessage('');
    const newItems = [];
    const errors = [];

    Array.from(filesArray).forEach((file) => {
      const error = validateFile(file, zoneKey);
      if (error) {
        errors.push(error);
      } else {
        const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : null;
        newItems.push({
          id: generateUUID(),
          file,
          zoneKey,
          filename: file.name,
          size: file.size,
          previewUrl,
          notes: '',
          progress: 0,
          status: 'Ready', // 'Ready' | 'Uploading' | 'Extracting AI...' | 'Saved' | 'Failed'
          errorText: null,
        });
      }
    });

    if (errors.length > 0) {
      setErrorMessage(errors.join(' '));
    }

    if (newItems.length > 0) {
      setStagedFiles((prev) => [...prev, ...newItems]);
    }
  };

  const handleNoteChange = (id, newNote) => {
    setStagedFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, notes: newNote } : item))
    );
  };

  const handleRemoveStaged = (id) => {
    setStagedFiles((prev) => {
      const item = prev.find((x) => x.id === id);
      if (item && item.previewUrl) {
        URL.revokeObjectURL(item.previewUrl);
      }
      return prev.filter((x) => x.id !== id);
    });
  };

  // Upload an individual file with real progress tracking & extraction feedback
  const uploadSingleItem = (item, activeCaseId) => {
    return new Promise((resolve) => {
      setStagedFiles((prev) =>
        prev.map((f) => (f.id === item.id ? { ...f, status: 'Uploading', progress: 10 } : f))
      );

      const formData = new FormData();
      formData.append('files', item.file);
      formData.append('notes', item.notes || '');

      const notesMap = {};
      if (item.notes) {
        notesMap[item.filename] = item.notes;
      }
      formData.append('notes_map', JSON.stringify(notesMap));

      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/api/cases/${activeCaseId}/evidence`);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.min(85, Math.round((event.loaded / event.total) * 100));
          setStagedFiles((prev) =>
            prev.map((f) =>
              f.id === item.id
                ? {
                    ...f,
                    progress: percentComplete,
                    status: percentComplete >= 80 ? 'Extracting AI...' : 'Uploading',
                  }
                : f
            )
          );
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          setStagedFiles((prev) =>
            prev.map((f) => (f.id === item.id ? { ...f, status: 'Saved', progress: 100 } : f))
          );
          resolve({ success: true, item });
        } else {
          let errDetail = 'Upload failed';
          try {
            const parsed = JSON.parse(xhr.responseText);
            if (parsed.detail) errDetail = parsed.detail;
          } catch (e) {
            errDetail = xhr.statusText || 'Server error';
          }
          setStagedFiles((prev) =>
            prev.map((f) =>
              f.id === item.id ? { ...f, status: 'Failed', progress: 100, errorText: errDetail } : f
            )
          );
          resolve({ success: false, item, error: errDetail });
        }
      };

      xhr.onerror = () => {
        setStagedFiles((prev) =>
          prev.map((f) =>
            f.id === item.id
              ? {
                  ...f,
                  status: 'Failed',
                  progress: 100,
                  errorText: 'Cannot connect to backend server (http://127.0.0.1:8000).',
                }
              : f
          )
        );
        resolve({ success: false, item, error: 'Network error' });
      };

      xhr.send(formData);
    });
  };

  // Upload all items currently in 'Ready' or 'Failed' status with duplicate prevention
  const handleUploadAll = async () => {
    if (isUploading) return;

    const readyItems = stagedFiles.filter((item) => item.status === 'Ready' || item.status === 'Failed');
    if (readyItems.length === 0) return;

    setIsUploading(true);
    setErrorMessage('');
    const targetCaseId = caseId || generateUUID();
    if (!caseId) {
      setCaseId(targetCaseId);
      setCaseInput(targetCaseId);
    }

    try {
      const results = [];
      for (const item of readyItems) {
        const res = await uploadSingleItem(item, targetCaseId);
        results.push(res);
      }

      // Refresh evidence list from server
      await fetchEvidence(targetCaseId);

      const failures = results.filter((r) => !r.success);
      if (failures.length === 0) {
        setSuccessMessage(`Successfully processed ${results.length} evidence file(s) with AI text extraction and SHA-256 integrity.`);
        setTimeout(() => setSuccessMessage(''), 4000);
      } else {
        setErrorMessage(`Completed with ${failures.length} failure(s). Check item status badges.`);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const copyToClipboard = (text, id) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedHash(id);
      setTimeout(() => setCopiedHash(null), 2000);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e, zoneKey) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActiveZone(zoneKey);
  };

  const handleDragLeave = (e, zoneKey) => {
    e.preventDefault();
    e.stopPropagation();
    if (dragActiveZone === zoneKey) {
      setDragActiveZone(null);
    }
  };

  const handleDrop = (e, zoneKey) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActiveZone(null);
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesAdded(e.dataTransfer.files, zoneKey);
    }
  };

  const readyCount = stagedFiles.filter((f) => f.status === 'Ready' || f.status === 'Failed').length;

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <div className="logo-shield">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="M9 12l2 2 4-4"/>
            </svg>
          </div>
          <div>
            <h1 className="brand-title">Evidence AI</h1>
            <p className="brand-tagline">Victim-First Digital Evidence Platform • Intake, Forensic Preservation & AI Extraction</p>
          </div>
        </div>

        <div className="privacy-badge">
          <span className="privacy-dot"></span>
          <span className="privacy-text">Files are processed locally and never sent to third parties.</span>
        </div>
      </header>

      {/* Case Management Bar */}
      <section className="case-bar-card">
        <div className="case-bar-content">
          <div className="case-input-group">
            <label htmlFor="caseIdInput" className="case-label">
              <svg className="case-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              Incident Case ID:
            </label>
            <input
              id="caseIdInput"
              type="text"
              className="case-input"
              value={caseInput}
              placeholder="Enter Case ID or auto-generate"
              disabled={isUploading}
              onChange={(e) => setCaseInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleApplyCaseId()}
            />
            <button className="btn btn-secondary" onClick={handleApplyCaseId} disabled={isUploading} title="Load evidence for this case">
              Set Case
            </button>
            <button className="btn btn-outline" onClick={handleNewCase} disabled={isUploading} title="Generate a new Case UUID">
              + New Case
            </button>
          </div>
          <div className="case-status-indicator">
            Active Case: <span className="case-active-id">{caseId}</span>
          </div>
        </div>
      </section>

      {/* Backend Offline Indicator Banner */}
      {backendOffline && (
        <div className="alert alert-warning" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>🔌</span>
            <div>
              <strong>Backend Offline:</strong> Python extraction server is not reachable at <code>http://127.0.0.1:8000</code>.
              Launch the backend to upload and process evidence.
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => fetchEvidence(caseId)}>
            ↻ Retry Connection
          </button>
        </div>
      )}

      {/* Inline Feedback Alerts */}
      {errorMessage && (
        <div className="alert alert-error">
          <div className="alert-icon">⚠️</div>
          <div className="alert-content">{errorMessage}</div>
          <button className="alert-close" onClick={() => setErrorMessage('')}>✕</button>
        </div>
      )}

      {successMessage && (
        <div className="alert alert-success">
          <div className="alert-icon">✓</div>
          <div className="alert-content">{successMessage}</div>
          <button className="alert-close" onClick={() => setSuccessMessage('')}>✕</button>
        </div>
      )}

      {/* Main Upload Section: Three Zones */}
      <section className="upload-zones-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Upload Evidence</h2>
            <p className="section-desc">
              Select or drag files into their designated category. Files are hashed, forensically preserved, and processed with local AI extraction (PaddleOCR / Faster-Whisper).
            </p>
          </div>

          {stagedFiles.length > 0 && (
            <div className="upload-actions">
              <button
                className="btn btn-primary"
                onClick={handleUploadAll}
                disabled={readyCount === 0 || isUploading}
              >
                {isUploading ? (
                  <>
                    <span className="spinner"></span>
                    Processing & Extracting...
                  </>
                ) : (
                  <>
                    <svg className="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    {readyCount > 0 ? `Upload & Extract ${readyCount} Item(s)` : 'All Files Uploaded'}
                  </>
                )}
              </button>
              <button
                className="btn btn-light"
                onClick={() => setStagedFiles([])}
                disabled={isUploading}
                title="Clear queue"
              >
                Clear Queue
              </button>
            </div>
          )}
        </div>

        <div className="zones-grid">
          {ZONES.map((zone) => {
            const isDraggedOver = dragActiveZone === zone.key;
            const zoneStaged = stagedFiles.filter((f) => f.zoneKey === zone.key);

            return (
              <div
                key={zone.key}
                className={`zone-card ${isDraggedOver ? 'zone-card-active' : ''}`}
                onDragOver={(e) => handleDragOver(e, zone.key)}
                onDragLeave={(e) => handleDragLeave(e, zone.key)}
                onDrop={(e) => handleDrop(e, zone.key)}
              >
                <div className="zone-header">
                  <div className="zone-icon-box">{zone.icon}</div>
                  <div>
                    <h3 className="zone-title">{zone.title}</h3>
                    <p className="zone-subtitle">{zone.subtitle}</p>
                  </div>
                </div>

                {/* Drop Area */}
                <label className={`zone-droparea ${isUploading ? 'disabled' : ''}`}>
                  <input
                    type="file"
                    multiple
                    disabled={isUploading}
                    accept={zone.accept}
                    className="zone-file-input"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        handleFilesAdded(e.target.files, zone.key);
                        e.target.value = '';
                      }
                    }}
                  />
                  <div className="droparea-content">
                    <p className="droparea-prompt">
                      <strong>Drag & drop files here</strong> or <span className="browse-link">browse</span>
                    </p>
                    <p className="droparea-formats">
                      Allowed: {zone.extensions.join(' ')} • Max: 50 MB
                    </p>
                  </div>
                </label>

                {/* Staged Items in this zone */}
                {zoneStaged.length > 0 && (
                  <div className="zone-staged-list">
                    <div className="staged-count-header">
                      Queued: {zoneStaged.length} file(s)
                    </div>
                    {zoneStaged.map((item) => (
                      <div key={item.id} className={`staged-item status-${item.status.toLowerCase().replace(/[^a-z]/g, '')}`}>
                        <div className="staged-item-main">
                          {item.previewUrl ? (
                            <img src={item.previewUrl} alt="Preview" className="staged-thumb" />
                          ) : (
                            <div className="staged-icon-fallback">{zone.icon}</div>
                          )}
                          <div className="staged-details">
                            <div className="staged-filename" title={item.filename}>
                              {item.filename}
                            </div>
                            <div className="staged-size">{formatBytes(item.size)}</div>
                          </div>
                          <div className="staged-badge-wrapper">
                            <span className={`badge badge-${item.status.toLowerCase().replace(/[^a-z]/g, '')}`}>
                              {(item.status === 'Uploading' || item.status === 'Extracting AI...') && <span className="spinner"></span>}
                              {item.status}
                            </span>
                            {item.status === 'Ready' && !isUploading && (
                              <button
                                className="item-remove-btn"
                                onClick={() => handleRemoveStaged(item.id)}
                                title="Remove file"
                              >
                                ✕
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Optional Notes Box */}
                        <div className="staged-notes-row">
                          <input
                            type="text"
                            placeholder="Optional note (e.g. WhatsApp chat from 12 March)"
                            className="staged-notes-input"
                            value={item.notes}
                            disabled={item.status === 'Uploading' || item.status === 'Extracting AI...' || item.status === 'Saved' || isUploading}
                            onChange={(e) => handleNoteChange(item.id, e.target.value)}
                          />
                        </div>

                        {/* Progress Bar */}
                        {(item.status === 'Uploading' || item.status === 'Extracting AI...' || item.status === 'Saved' || item.status === 'Failed') && (
                          <div className="progress-container">
                            <div
                              className={`progress-bar progress-${item.status.toLowerCase().replace(/[^a-z]/g, '')}`}
                              style={{ width: `${item.progress}%` }}
                            ></div>
                          </div>
                        )}

                        {item.errorText && (
                          <div className="item-error-msg">{item.errorText}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Evidence Table in this Case */}
      <section className="evidence-table-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Evidence in this Case</h2>
            <p className="section-desc">
              Immutable ledger of evidence saved with cryptographic SHA-256 fingerprinting and local AI extraction.
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => fetchEvidence(caseId)} disabled={isLoadingEvidence}>
            ↻ Refresh Records
          </button>
        </div>

        {isLoadingEvidence ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Loading preserved evidence records...</span>
          </div>
        ) : evidenceList.length === 0 ? (
          <div className="empty-state">
            <svg className="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
              <polyline points="13 2 13 9 20 9"/>
            </svg>
            <h3>No evidence items uploaded yet for this case</h3>
            <p>Upload screenshots, audio recordings, or text exports above to record and extract them securely.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="evidence-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Category</th>
                  <th>Extracted Intelligence</th>
                  <th>Size</th>
                  <th>Upload Time</th>
                  <th>SHA-256 Fingerprint</th>
                  <th>Authenticity</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {evidenceList.map((item) => {
                  const truncatedHash = `${item.sha256.substring(0, 10)}...${item.sha256.substring(item.sha256.length - 8)}`;
                  const isCopied = copiedHash === item.id;
                  const uploadDate = new Date(item.uploaded_at).toLocaleString();
                  const isExpanded = expandedRows.has(item.id);

                  let parsedMeta = null;
                  try {
                    parsedMeta = typeof item.extraction_metadata === 'string' ? JSON.parse(item.extraction_metadata) : item.extraction_metadata;
                  } catch (e) {}

                  return (
                    <tr key={item.id}>
                      <td className="col-filename">
                        <span className="file-icon-small">
                          {item.file_type === 'image' && '🖼️'}
                          {item.file_type === 'audio' && '🎙️'}
                          {item.file_type === 'text' && '📄'}
                        </span>
                        <strong title={item.original_filename}>{item.original_filename}</strong>
                        {item.notes && <div className="text-muted" style={{ fontSize: '11px', marginTop: '2px' }}>{item.notes}</div>}
                      </td>
                      <td>
                        <span className={`tag tag-${item.file_type}`}>
                          {item.file_type.toUpperCase()}
                        </span>
                      </td>
                      <td className="col-extraction">
                        {item.extracted_text ? (
                          <div className="extraction-summary">
                            <div className="extraction-header-badges">
                              {item.extraction_confidence != null && (
                                <span
                                  className={`badge-confidence ${item.extraction_confidence < 0.8 ? 'confidence-mid' : ''}`}
                                  title="Recognition Confidence"
                                >
                                  {(item.extraction_confidence * 100).toFixed(1)}% Conf
                                </span>
                              )}
                              {item.processing_time_ms != null && (
                                <span className="badge-diagnostic" title="Processing Time Diagnostics">
                                  ⚡ {item.processing_time_ms > 1000 ? (item.processing_time_ms / 1000).toFixed(2) + 's' : Math.round(item.processing_time_ms) + 'ms'}
                                </span>
                              )}
                            </div>
                            <div className="extraction-text-snippet">
                              {item.extracted_text.length > 120
                                ? item.extracted_text.substring(0, 120) + '...'
                                : item.extracted_text}
                            </div>
                            <button
                              className="btn-xs-link"
                              onClick={() => toggleExpandRow(item.id)}
                            >
                              {isExpanded ? 'Hide Details ▲' : 'View Full Intelligence ▼'}
                            </button>

                            {isExpanded && (
                              <div className="extraction-expand-panel">
                                <div style={{ marginBottom: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <strong>Extracted Content:</strong>
                                  <button
                                    className="btn-xs-link"
                                    onClick={() => copyToClipboard(item.extracted_text, `txt-${item.id}`)}
                                  >
                                    {copiedHash === `txt-${item.id}` ? '✓ Copied' : 'Copy Text'}
                                  </button>
                                </div>
                                <div className="extraction-full-text">{item.extracted_text}</div>

                                {parsedMeta && parsedMeta.segments && parsedMeta.segments.length > 0 && (
                                  <div>
                                    <strong style={{ fontSize: '11px' }}>Audio Segments & Timestamps:</strong>
                                    <div className="segments-list">
                                      {parsedMeta.segments.map((seg, sIdx) => (
                                        <div key={sIdx} className="segment-item">
                                          <span className="segment-timestamp">[{seg.start}s → {seg.end}s]</span>
                                          <span className="segment-text">{seg.text}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ) : (
                          <em className="text-muted" style={{ fontSize: '12px' }}>No text detected</em>
                        )}
                      </td>
                      <td className="col-size">{formatBytes(item.size_bytes)}</td>
                      <td className="col-time">{uploadDate}</td>
                      <td className="col-hash">
                        <button
                          className={`hash-copy-btn ${isCopied ? 'copied' : ''}`}
                          onClick={() => copyToClipboard(item.sha256, item.id)}
                          title="Click to copy full 256-bit hash"
                        >
                          <code>{truncatedHash}</code>
                          <span className="copy-icon">{isCopied ? '✓ Copied' : '📋'}</span>
                        </button>
                      </td>
                      <td>
                        {item.authenticity_passed ? (
                          <span className="badge badge-verified" title="Passed initial authenticity check">
                            ✓ Verified
                          </span>
                        ) : (
                          <span className="badge badge-failed">Flagged</span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <a
                            href={`${API_BASE}/api/evidence/${item.id}/file`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-outline btn-xs"
                            title="Download original untouched file"
                          >
                            Download
                          </a>
                          <button
                            className="btn btn-outline btn-xs"
                            onClick={() => handleReExtract(item.id)}
                            disabled={reExtractingId === item.id}
                            title="Re-run AI extraction"
                          >
                            {reExtractingId === item.id ? '...' : '↻ Re-AI'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Forensic Guarantee Banner */}
      <footer className="footer-card">
        <div className="forensic-guarantee">
          <div className="forensic-shield">⚖️</div>
          <div>
            <strong>Forensic Preservation Assurance:</strong> All evidence files are stored untouched in local storage
            (<code>storage/originals/</code>), cryptographically fingerprinted using SHA-256, logged to an
            append-only audit trail, and transcribed locally with PaddleOCR and Faster-Whisper.
          </div>
        </div>
      </footer>
    </div>
  );
}
