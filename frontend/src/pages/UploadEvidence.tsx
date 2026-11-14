import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { Upload, X, Check, AlertCircle } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/common/Button';

const ALLOWED_EXTENSIONS = new Set([
  'png', 'jpg', 'jpeg', 'webp',
  'mp3', 'wav', 'm4a', 'ogg',
  'txt', 'json', 'csv', 'eml', 'pdf'
]);

const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

interface StagedFile {
  id: string;
  file: File;
  notes: string;
}

export const UploadEvidence: React.FC = () => {
  const navigate = useNavigate();
  const { cases, activeCaseId, uploadEvidence } = useApp();

  const [selectedCaseId, setSelectedCaseId] = useState<string>(
    activeCaseId || (cases.length > 0 ? cases[0].id : '')
  );
  const [newCaseIdInput, setNewCaseIdInput] = useState<string>('');
  const [isCreatingNewCase, setIsCreatingNewCase] = useState<boolean>(cases.length === 0);

  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadSuccessCaseId, setUploadSuccessCaseId] = useState<string | null>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const onDrop = (acceptedFiles: File[]) => {
    setErrorMessage('');
    const newStaged: StagedFile[] = [];

    acceptedFiles.forEach((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';

      if (!ALLOWED_EXTENSIONS.has(ext)) {
        setErrorMessage(`File "${file.name}" has an unsupported format (.${ext}).`);
        return;
      }

      if (file.size > MAX_SIZE_BYTES) {
        setErrorMessage(`File "${file.name}" exceeds the 50 MB limit (${formatBytes(file.size)}).`);
        return;
      }

      newStaged.push({
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        file,
        notes: ''
      });
    });

    if (newStaged.length > 0) {
      setStagedFiles((prev) => [...prev, ...newStaged]);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true
  });

  const handleRemoveStaged = (id: string) => {
    setStagedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleNoteChange = (id: string, notes: string) => {
    setStagedFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, notes } : f))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (stagedFiles.length === 0) return;

    let targetCase = selectedCaseId.trim();
    if (isCreatingNewCase) {
      targetCase = newCaseIdInput.trim() || crypto.randomUUID();
    }

    if (!targetCase) {
      setErrorMessage('Please select or specify a case for this evidence.');
      return;
    }

    setIsUploading(true);
    setErrorMessage('');

    try {
      const notesMap: Record<string, string> = {};
      stagedFiles.forEach((item) => {
        if (item.notes.trim()) {
          notesMap[item.file.name] = item.notes.trim();
        }
      });

      const files = stagedFiles.map((s) => s.file);
      await uploadEvidence(targetCase, files, notesMap);

      setStagedFiles([]);
      setUploadSuccessCaseId(targetCase);
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="pb-3 border-b border-[#E6E4DF]">
        <h1 className="text-lg font-semibold text-[#1C1917]">Add evidence</h1>
        <p className="text-xs text-[#6B6862] mt-0.5">
          Your files stay on this device. Nothing is sent anywhere.
        </p>
      </div>

      {uploadSuccessCaseId && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-900 flex items-center justify-between">
          <span>Files saved and fingerprinted under case [{uploadSuccessCaseId}].</span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate(`/cases/${uploadSuccessCaseId}`)}
          >
            View case
          </Button>
        </div>
      )}

      {errorMessage && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Case Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-medium text-[#1C1917]">
            Associate with case
          </label>

          {cases.length > 0 && (
            <div className="flex items-center gap-4 text-xs text-[#6B6862] mb-1">
              <label className="inline-flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="caseChoice"
                  checked={!isCreatingNewCase}
                  onChange={() => setIsCreatingNewCase(false)}
                  className="accent-[#0F766E]"
                />
                Existing case
              </label>
              <label className="inline-flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="caseChoice"
                  checked={isCreatingNewCase}
                  onChange={() => setIsCreatingNewCase(true)}
                  className="accent-[#0F766E]"
                />
                New case
              </label>
            </div>
          )}

          {!isCreatingNewCase && cases.length > 0 ? (
            <select
              value={selectedCaseId}
              onChange={(e) => setSelectedCaseId(e.target.value)}
              className="w-full bg-white border border-[#E6E4DF] rounded px-3 py-2 text-xs text-[#1C1917] font-mono focus:outline-none focus:border-[#0F766E]"
            >
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} ({c.evidence_count || 0} files)
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={newCaseIdInput}
              onChange={(e) => setNewCaseIdInput(e.target.value)}
              placeholder="Enter a new case ID, or leave blank to auto-generate"
              className="w-full bg-white border border-[#E6E4DF] rounded px-3 py-2 text-xs text-[#1C1917] font-mono placeholder:font-sans focus:outline-none focus:border-[#0F766E]"
            />
          )}
        </div>

        {/* Dropzone */}
        <div>
          <label className="block text-xs font-medium text-[#1C1917] mb-1">
            Files
          </label>
          <div
            {...getRootProps()}
            className={`border border-dashed rounded p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-[#0F766E] bg-[#F0FDFA]'
                : 'border-[#D6D3CD] bg-white hover:border-[#A8A29E]'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="w-5 h-5 text-[#6B6862] mx-auto mb-2" />
            <p className="text-xs font-medium text-[#1C1917]">
              {isDragActive ? 'Drop files here' : 'Drag files here, or click to browse'}
            </p>
            <p className="text-[11px] text-[#6B6862] mt-1">
              Images (PNG, JPG, WEBP), Audio (MP3, WAV, M4A), Text (TXT, JSON, CSV, EML, PDF) • Up to 50 MB
            </p>
          </div>
        </div>

        {/* Staged file list */}
        {stagedFiles.length > 0 && (
          <div className="space-y-2">
            <label className="block text-xs font-medium text-[#1C1917]">
              Files to add ({stagedFiles.length})
            </label>
            <div className="border border-[#E6E4DF] rounded bg-white divide-y divide-[#E6E4DF]">
              {stagedFiles.map((item) => (
                <div key={item.id} className="p-3 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-medium text-[#1C1917] truncate">
                        {item.file.name}
                      </span>
                      <span className="text-[11px] text-[#6B6862] font-mono shrink-0">
                        {formatBytes(item.file.size)}
                      </span>
                    </div>
                    <input
                      type="text"
                      placeholder="Optional note (e.g. WhatsApp screenshot from 12 March)"
                      value={item.notes}
                      onChange={(e) => handleNoteChange(item.id, e.target.value)}
                      className="w-full bg-[#FBFBF9] border border-[#E6E4DF] rounded px-2.5 py-1 text-xs text-[#1C1917] placeholder:text-[#9C9890] focus:outline-none focus:border-[#0F766E]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveStaged(item.id)}
                    className="p-1 text-[#9C9890] hover:text-rose-600 rounded"
                    title="Remove file"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-2">
          {stagedFiles.length > 0 && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setStagedFiles([])}
              disabled={isUploading}
            >
              Clear
            </Button>
          )}
          <Button
            type="submit"
            variant="primary"
            size="sm"
            isLoading={isUploading}
            disabled={stagedFiles.length === 0}
          >
            Save evidence
          </Button>
        </div>
      </form>
    </div>
  );
};
