import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Download, 
  Trash2, 
  Briefcase, 
  FileText, 
  Image as ImageIcon, 
  Mic, 
  FileCheck, 
  Calendar, 
  HardDrive, 
  ShieldCheck, 
  Copy, 
  Check, 
  Edit3, 
  ZoomIn, 
  ZoomOut,
  ExternalLink,
  Save
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { EvidenceTypeBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { AudioPlayer } from '../components/common/AudioPlayer';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const EvidenceDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { evidence, cases, updateEvidenceItem, deleteEvidenceItem } = useApp();

  const file = evidence.find((e) => e.id === id);

  const [copiedHash, setCopiedHash] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<boolean>(false);
  const [imageZoom, setImageZoom] = useState<number>(1);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState<boolean>(false);

  // Editable fields
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [displayName, setDisplayName] = useState<string>(file?.displayName || '');
  const [notes, setNotes] = useState<string>(file?.notes || '');
  const [caseId, setCaseId] = useState<string>(file?.caseId || '');

  if (!file) {
    return (
      <div className="text-center py-20 bg-[#162032] border border-slate-800 rounded-2xl">
        <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h2 className="text-base font-semibold text-white mb-2">Evidence Item Not Found</h2>
        <p className="text-xs text-slate-400 mb-4">The evidence file ID "{id}" does not exist in the vault.</p>
        <Button variant="primary" size="sm" onClick={() => navigate('/vault')}>
          Return to Vault
        </Button>
      </div>
    );
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleCopyHash = () => {
    if (file.metadata.sha256) {
      navigator.clipboard.writeText(file.metadata.sha256);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(file.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleSaveMetadata = async () => {
    await updateEvidenceItem(file.id, {
      displayName: displayName.trim() || file.fileName,
      notes: notes.trim(),
      caseId: caseId
    });
    setIsEditing(false);
  };

  const handleDownload = () => {
    if (file.fileObject) {
      const url = URL.createObjectURL(file.fileObject);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.fileName;
      a.click();
      URL.revokeObjectURL(url);
    } else if (file.textContent) {
      const blob = new Blob([file.textContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.fileName;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      const blob = new Blob([`Preserved Evidence File: ${file.fileName}\nSHA-256: ${file.metadata.sha256}`], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.fileName;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleConfirmDelete = async () => {
    await deleteEvidenceItem(file.id);
    navigate('/vault');
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Navigation */}
      <div>
        <button
          onClick={() => navigate('/vault')}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Evidence Vault
        </button>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                {file.id}
              </span>
              <EvidenceTypeBadge type={file.fileType} />
              <span className="text-[11px] font-mono text-slate-400">
                {file.fileName}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{file.displayName}</h1>
          </div>

          <div className="flex items-center gap-2.5">
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="w-4 h-4 text-cyan-400" />
              <span>Download Original</span>
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setIsDeleteDialogOpen(true)} className="text-rose-400 hover:bg-rose-500/10">
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Preview & Right Metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Section: File Preview (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-[#162032] border border-slate-800 rounded-2xl overflow-hidden shadow-soft">
            <div className="p-3 bg-[#0F172A] border-b border-slate-800 flex items-center justify-between text-xs text-slate-300">
              <span className="font-semibold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Raw File Inspection Preview
              </span>

              {file.fileType === 'image' && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setImageZoom((z) => Math.max(0.5, z - 0.25))}
                    className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <span className="text-[11px] font-mono text-slate-400 w-10 text-center">
                    {Math.round(imageZoom * 100)}%
                  </span>
                  <button
                    onClick={() => setImageZoom((z) => Math.min(2.5, z + 0.25))}
                    className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>

            <div className="p-6 flex items-center justify-center min-h-[380px] bg-[#070b14]/50 overflow-auto">
              {/* Image Preview */}
              {file.fileType === 'image' && (
                <div className="overflow-auto max-h-[500px] w-full flex items-center justify-center">
                  <img
                    src={file.previewUrl}
                    alt={file.displayName}
                    style={{ transform: `scale(${imageZoom})`, transformOrigin: 'center' }}
                    className="max-h-[460px] rounded-lg shadow-lg object-contain transition-transform duration-150"
                  />
                </div>
              )}

              {/* Audio Player Preview */}
              {file.fileType === 'audio' && (
                <div className="w-full max-w-md my-auto">
                  <AudioPlayer src={file.audioUrl} title={file.displayName} />
                </div>
              )}

              {/* Text / Chat Log Preview */}
              {file.fileType === 'text' && (
                <div className="w-full h-full max-h-[480px] overflow-auto bg-[#0B1120] border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {file.textContent || 'No text preview available for this log file.'}
                </div>
              )}

              {/* Document Preview Placeholder */}
              {file.fileType === 'document' && (
                <div className="text-center p-8 space-y-4">
                  <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mx-auto">
                    <FileText className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">{file.fileName}</h3>
                    <p className="text-xs text-slate-400 mt-1 max-w-md">
                      {file.fileExtension.toUpperCase()} document ({formatBytes(file.fileSize)}).
                      Click below to view or export the preserved binary document.
                    </p>
                  </div>
                  <Button variant="primary" size="sm" onClick={handleDownload}>
                    <Download className="w-4 h-4" /> Download Original Document
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Section: Metadata & Case Association (5 Cols) */}
        <div className="lg:col-span-5 space-y-5">
          {/* Metadata Card */}
          <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6 space-y-5 shadow-soft">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
                Evidence Record Details
              </h3>
              {isEditing ? (
                <Button variant="cyan" size="sm" onClick={handleSaveMetadata}>
                  <Save className="w-3.5 h-3.5" /> Save
                </Button>
              ) : (
                <button
                  onClick={() => setIsEditing(true)}
                  className="p-1.5 text-xs text-slate-400 hover:text-white flex items-center gap-1 rounded hover:bg-slate-800"
                >
                  <Edit3 className="w-3.5 h-3.5" /> Edit
                </button>
              )}
            </div>

            {/* Display Title */}
            <div>
              <span className="text-[11px] text-slate-400 block mb-1">Display Label</span>
              {isEditing ? (
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
              ) : (
                <span className="text-sm font-semibold text-white">{file.displayName}</span>
              )}
            </div>

            {/* Case Association */}
            <div>
              <span className="text-[11px] text-slate-400 block mb-1">Associated Case</span>
              {isEditing ? (
                <select
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.id} — {c.title}
                    </option>
                  ))}
                </select>
              ) : (
                <button
                  onClick={() => navigate(`/cases/${file.caseId}`)}
                  className="text-xs font-mono text-blue-400 hover:underline flex items-center gap-1.5"
                >
                  <Briefcase className="w-3.5 h-3.5" />
                  {file.caseId} <ExternalLink className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Notes */}
            <div>
              <span className="text-[11px] text-slate-400 block mb-1">Investigative Context / Notes</span>
              {isEditing ? (
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 resize-none"
                />
              ) : (
                <p className="text-xs text-slate-300 leading-relaxed bg-[#0F172A] border border-slate-800 p-3 rounded-lg">
                  {file.notes || <em className="text-slate-500">No notes recorded for this item.</em>}
                </p>
              )}
            </div>

            {/* Technical Specs List */}
            <div className="pt-3 border-t border-slate-800 space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Evidence ID</span>
                <button
                  onClick={handleCopyId}
                  className="font-mono text-slate-200 hover:text-white flex items-center gap-1"
                >
                  <span>{file.id}</span>
                  {copiedId ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-500" />}
                </button>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-400">Original Filename</span>
                <span className="font-mono text-slate-200">{file.fileName}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-400">File Size</span>
                <span className="font-mono text-slate-200">{formatBytes(file.fileSize)}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-400">MIME Type</span>
                <span className="font-mono text-slate-200">{file.metadata.mimeType}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-400">Date Preserved</span>
                <span className="font-mono text-slate-200">
                  {new Date(file.dateAdded).toLocaleString()}
                </span>
              </div>
            </div>

            {/* SHA-256 Cryptographic Box */}
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                  SHA-256 Hash
                </span>
                <button
                  onClick={handleCopyHash}
                  className="text-[10px] font-medium text-cyan-400 hover:underline flex items-center gap-1"
                >
                  {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copiedHash ? 'Copied' : 'Copy'}
                </button>
              </div>
              <div className="font-mono text-[11px] text-slate-300 break-all select-all leading-snug">
                {file.metadata.sha256 || 'Uncalculated'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Item Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        onClose={() => setIsDeleteDialogOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Evidence Item?"
        message={`Are you sure you want to remove "${file.displayName}" from the vault? This action cannot be undone.`}
      />
    </div>
  );
};
