import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { 
  UploadCloud, 
  Image as ImageIcon, 
  Mic, 
  FileText, 
  FileCode, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Briefcase, 
  Check, 
  Layers, 
  FileCheck,
  ShieldCheck
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { EvidenceType, StagedUploadItem } from '../types';
import { Button } from '../components/common/Button';
import { EvidenceTypeBadge } from '../components/common/Badge';

const ALLOWED_EXTENSIONS: Record<string, EvidenceType> = {
  // Images
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  webp: 'image',
  // Audio
  mp3: 'audio',
  wav: 'audio',
  m4a: 'audio',
  ogg: 'audio',
  // Text / Logs
  txt: 'text',
  csv: 'text',
  json: 'text',
  eml: 'text',
  // Documents
  pdf: 'document',
  docx: 'document'
};

const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

// Browser-native SHA-256 calculation
async function computeBrowserSha256(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

export const UploadEvidence: React.FC = () => {
  const navigate = useNavigate();
  const { cases, activeCaseId, addEvidenceItem } = useApp();

  const [selectedCaseId, setSelectedCaseId] = useState<string>(activeCaseId || (cases[0]?.id || ''));
  const [stagedFiles, setStagedFiles] = useState<StagedUploadItem[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string>('');
  const [completedCount, setCompletedCount] = useState<number>(0);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setGeneralError('');
    const newItems: StagedUploadItem[] = [];

    acceptedFiles.forEach((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      const category = ALLOWED_EXTENSIONS[ext];

      if (!category) {
        setGeneralError(`File "${file.name}" has unsupported format .${ext}`);
        return;
      }

      if (file.size > MAX_SIZE_BYTES) {
        setGeneralError(`File "${file.name}" exceeds 50 MB limit (${formatBytes(file.size)})`);
        return;
      }

      const previewUrl = category === 'image' ? URL.createObjectURL(file) : undefined;

      newItems.push({
        id: `upload-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
        file,
        caseId: selectedCaseId,
        fileType: category,
        displayName: file.name.replace(/\.[^/.]+$/, ''),
        notes: '',
        progress: 0,
        status: 'queued',
        previewUrl
      });
    });

    if (newItems.length > 0) {
      setStagedFiles((prev) => [...prev, ...newItems]);
    }
  }, [selectedCaseId]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  });

  const handleRemoveStaged = (id: string) => {
    setStagedFiles((prev) => {
      const item = prev.find((x) => x.id === id);
      if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl);
      return prev.filter((x) => x.id !== id);
    });
  };

  const handleDisplayNameChange = (id: string, name: string) => {
    setStagedFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, displayName: name } : item))
    );
  };

  const handleNotesChange = (id: string, notes: string) => {
    setStagedFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, notes } : item))
    );
  };

  // Commit and ingest files locally
  const handleCommitUploads = async () => {
    if (stagedFiles.length === 0 || !selectedCaseId) return;

    setIsProcessing(true);
    setGeneralError('');
    let successCounter = 0;

    for (const item of stagedFiles) {
      if (item.status === 'completed') continue;

      // Update item progress
      setStagedFiles((prev) =>
        prev.map((f) => (f.id === item.id ? { ...f, status: 'validating', progress: 30 } : f))
      );

      try {
        // Real browser-side cryptographic hashing
        const sha256Hash = await computeBrowserSha256(item.file);

        setStagedFiles((prev) =>
          prev.map((f) => (f.id === item.id ? { ...f, status: 'uploading', progress: 75 } : f))
        );

        // Read text content if applicable
        let textContent: string | undefined = undefined;
        if (item.fileType === 'text') {
          textContent = await item.file.text();
        }

        // Add to local app state vault
        const ext = item.file.name.split('.').pop()?.toLowerCase() || '';
        await addEvidenceItem({
          caseId: selectedCaseId,
          fileName: item.file.name,
          displayName: item.displayName || item.file.name,
          fileType: item.fileType,
          fileExtension: ext,
          fileSize: item.file.size,
          notes: item.notes,
          previewUrl: item.previewUrl,
          fileObject: item.file,
          textContent,
          metadata: {
            sha256: sha256Hash,
            mimeType: item.file.type || 'application/octet-stream',
            authenticityStatus: 'Verified',
            authorOrSource: 'Browser Local File Intake'
          }
        });

        setStagedFiles((prev) =>
          prev.map((f) => (f.id === item.id ? { ...f, status: 'completed', progress: 100 } : f))
        );
        successCounter++;
      } catch (err: any) {
        setStagedFiles((prev) =>
          prev.map((f) =>
            f.id === item.id ? { ...f, status: 'error', progress: 100, errorMessage: err.message || 'Intake failed' } : f
          )
        );
      }
    }

    setCompletedCount(successCounter);
    setIsProcessing(false);
  };

  const queuedCount = stagedFiles.filter((f) => f.status === 'queued').length;
  const targetCase = cases.find((c) => c.id === selectedCaseId);

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-fadeIn">
      {/* Header */}
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <UploadCloud className="w-6 h-6 text-cyan-400" />
          Evidence Intake & Upload
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Select or drag sensitive files to compute cryptographic SHA-256 hashes and preserve chain of custody.
        </p>
      </div>

      {/* Case Selector Banner */}
      <div className="bg-[#162032] border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center shrink-0">
            <Briefcase className="w-5 h-5" />
          </div>
          <div>
            <label className="text-xs font-semibold text-white block">Destination Investigation Case</label>
            <span className="text-[11px] text-slate-400">All uploaded evidence will be grouped under this case.</span>
          </div>
        </div>

        <select
          value={selectedCaseId}
          onChange={(e) => setSelectedCaseId(e.target.value)}
          className="bg-[#0F172A] border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-slate-200 font-medium focus:outline-none focus:border-blue-500 cursor-pointer min-w-[260px]"
        >
          {cases.map((c) => (
            <option key={c.id} value={c.id}>
              {c.id} — {c.title}
            </option>
          ))}
        </select>
      </div>

      {generalError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{generalError}</span>
        </div>
      )}

      {/* Drag & Drop Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
          isDragActive
            ? 'border-cyan-400 bg-cyan-500/5 shadow-glow-cyan'
            : 'border-slate-700/80 bg-[#162032]/50 hover:border-slate-600 hover:bg-[#162032]'
        }`}
      >
        <input {...getInputProps()} />
        <div className="max-w-md mx-auto space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mx-auto shadow-sm">
            <UploadCloud className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">
              {isDragActive ? 'Drop files here to stage' : 'Drag & drop evidence files here'}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              or <span className="text-cyan-400 font-semibold underline">browse from your computer</span>
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-1.5 text-[11px] font-mono text-slate-400 pt-2">
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-purple-400">PNG, JPG, WEBP</span>
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-400">MP3, WAV, M4A</span>
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-amber-400">TXT, JSON, CSV, EML</span>
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-blue-400">PDF, DOCX</span>
          </div>
          <p className="text-[11px] text-slate-400">Maximum file size: 50 MB per file</p>
        </div>
      </div>

      {/* Upload Queue Section */}
      {stagedFiles.length > 0 && (
        <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Staged Evidence Queue ({stagedFiles.length} file{stagedFiles.length > 1 ? 's' : ''})
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Add descriptive labels and notes before committing to the local vault.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStagedFiles([])}
                disabled={isProcessing}
              >
                Clear All
              </Button>
              <Button
                variant="cyan"
                size="sm"
                onClick={handleCommitUploads}
                isLoading={isProcessing}
                disabled={queuedCount === 0}
              >
                <ShieldCheck className="w-4 h-4" />
                <span>
                  {queuedCount > 0 ? `Commit & Hash ${queuedCount} File(s)` : 'All Preserved'}
                </span>
              </Button>
            </div>
          </div>

          {/* Staged Cards List */}
          <div className="space-y-3">
            {stagedFiles.map((item) => (
              <div
                key={item.id}
                className="bg-[#0F172A] border border-slate-700/70 rounded-xl p-4 space-y-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    {item.previewUrl ? (
                      <img src={item.previewUrl} alt="preview" className="w-12 h-12 rounded-lg object-cover border border-slate-700" />
                    ) : (
                      <div className="w-12 h-12 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                        {item.fileType === 'audio' && <Mic className="w-6 h-6 text-cyan-400" />}
                        {item.fileType === 'document' && <FileText className="w-6 h-6 text-blue-400" />}
                        {item.fileType === 'text' && <FileCode className="w-6 h-6 text-amber-400" />}
                        {item.fileType === 'image' && <ImageIcon className="w-6 h-6 text-purple-400" />}
                      </div>
                    )}

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white truncate">{item.file.name}</span>
                        <EvidenceTypeBadge type={item.fileType} />
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">
                        {formatBytes(item.file.size)} • Type: {item.fileType}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {item.status === 'completed' && (
                      <span className="text-xs font-medium text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" /> Saved & Hashed
                      </span>
                    )}
                    {item.status === 'validating' && (
                      <span className="text-xs font-mono text-cyan-400 animate-pulse">Hashing raw bytes...</span>
                    )}
                    {item.status === 'uploading' && (
                      <span className="text-xs font-mono text-blue-400 animate-pulse">Storing untouched...</span>
                    )}
                    {item.status === 'queued' && (
                      <button
                        onClick={() => handleRemoveStaged(item.id)}
                        className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800"
                        title="Remove from queue"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress bar */}
                {item.progress > 0 && (
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        item.status === 'completed' ? 'bg-emerald-400' : 'bg-cyan-400'
                      }`}
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                )}

                {/* Edit display title & notes */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  <input
                    type="text"
                    value={item.displayName}
                    disabled={item.status === 'completed'}
                    onChange={(e) => handleDisplayNameChange(item.id, e.target.value)}
                    placeholder="Evidence display title..."
                    className="bg-[#162032] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                  <input
                    type="text"
                    value={item.notes}
                    disabled={item.status === 'completed'}
                    onChange={(e) => handleNotesChange(item.id, e.target.value)}
                    placeholder="Optional notes (e.g. WhatsApp screenshot from 12 March)..."
                    className="bg-[#162032] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            ))}
          </div>

          {completedCount > 0 && (
            <div className="flex items-center justify-between p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Successfully committed {completedCount} evidence item(s) to case [{selectedCaseId}].
              </span>
              <Button variant="outline" size="sm" onClick={() => navigate('/vault')}>
                Open Vault →
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Explanatory Protocol Note */}
      <div className="p-4 rounded-2xl bg-[#162032] border border-slate-800 text-xs text-slate-400 space-y-1">
        <p className="font-semibold text-slate-300">Browser-Side Prototype Intake Protocol</p>
        <p className="text-[11px] leading-relaxed">
          Files are preserved untouched in the current browser session with SHA-256 integrity hashing.
          In the future backend phase, this upload handler will stream raw byte arrays directly to FastAPI.
        </p>
      </div>
    </div>
  );
};
