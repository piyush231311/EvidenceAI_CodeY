import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Download, Trash2, Copy, Check, Upload, Files } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { EvidenceFile } from '../types';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const EvidenceVault: React.FC = () => {
  const navigate = useNavigate();
  const { evidence, deleteEvidence, isLoading } = useApp();

  const [search, setSearch] = useState<string>('');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<EvidenceFile | null>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const handleCopyHash = (hash: string, id: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleConfirmDelete = async () => {
    if (deleteTarget) {
      await deleteEvidence(deleteTarget.id);
      setDeleteTarget(null);
    }
  };

  const filteredEvidence = evidence.filter((item) => {
    const q = search.toLowerCase();
    return (
      item.original_filename.toLowerCase().includes(q) ||
      item.case_id.toLowerCase().includes(q) ||
      item.sha256.toLowerCase().includes(q) ||
      (item.notes && item.notes.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E6E4DF]">
        <div>
          <h1 className="text-lg font-semibold text-[#1C1917]">Evidence</h1>
          <p className="text-xs text-[#6B6862] mt-0.5">
            All preserved files across your cases with SHA-256 fingerprints.
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={() => navigate('/upload')}>
          <Upload className="w-3.5 h-3.5" />
          <span>Add evidence</span>
        </Button>
      </div>

      {/* Filter / Search input */}
      {evidence.length > 0 && (
        <div className="relative max-w-sm">
          <Search className="w-3.5 h-3.5 text-[#9C9890] absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by filename, case ID, or hash..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-[#E6E4DF] rounded pl-8 pr-3 py-1.5 text-xs text-[#1C1917] placeholder:text-[#9C9890] focus:outline-none focus:border-[#0F766E]"
          />
        </div>
      )}

      {/* Evidence Content */}
      {isLoading ? (
        <div className="py-12 text-center text-xs text-[#6B6862]">Loading evidence...</div>
      ) : evidence.length === 0 ? (
        <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-8">
          <Files className="w-8 h-8 text-[#9C9890] mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No evidence added yet</h3>
          <p className="text-xs text-[#6B6862] mb-4">
            Upload images, voice recordings, or text exports to preserve them securely.
          </p>
          <Button variant="primary" size="sm" onClick={() => navigate('/upload')}>
            Add evidence
          </Button>
        </div>
      ) : filteredEvidence.length === 0 ? (
        <div className="py-8 text-center text-xs text-[#6B6862]">
          No evidence files match "{search}".
        </div>
      ) : (
        <div className="bg-white border border-[#E6E4DF] rounded-md overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#E6E4DF] bg-[#F9F9F7] text-[#6B6862]">
                <th className="py-2.5 px-4 font-medium">Filename</th>
                <th className="py-2.5 px-4 font-medium">Case</th>
                <th className="py-2.5 px-4 font-medium">Type</th>
                <th className="py-2.5 px-4 font-medium">Size</th>
                <th className="py-2.5 px-4 font-medium">SHA-256 hash</th>
                <th className="py-2.5 px-4 font-medium">Notes</th>
                <th className="py-2.5 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E6E4DF]">
              {filteredEvidence.map((file) => {
                const truncatedHash = `${file.sha256.substring(0, 8)}...${file.sha256.substring(file.sha256.length - 6)}`;
                const isCopied = copiedHash === file.id;

                return (
                  <tr key={file.id} className="hover:bg-[#F9F9F7] transition-colors">
                    <td className="py-3 px-4 font-medium text-[#1C1917] max-w-xs truncate" title={file.original_filename}>
                      {file.original_filename}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => navigate(`/cases/${file.case_id}`)}
                        className="font-mono text-xs text-[#0F766E] hover:underline"
                      >
                        {file.case_id.substring(0, 10)}...
                      </button>
                    </td>
                    <td className="py-3 px-4 text-[#6B6862] uppercase text-[11px]">
                      {file.file_type}
                    </td>
                    <td className="py-3 px-4 text-[#6B6862] font-mono text-[11px]">
                      {formatBytes(file.size_bytes)}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleCopyHash(file.sha256, file.id)}
                        className="inline-flex items-center gap-1 font-mono text-[11px] text-[#6B6862] hover:text-[#1C1917]"
                        title="Click to copy full SHA-256 hash"
                      >
                        <code>{truncatedHash}</code>
                        {isCopied ? <Check className="w-3 h-3 text-[#0F766E]" /> : <Copy className="w-3 h-3 text-[#9C9890]" />}
                      </button>
                    </td>
                    <td className="py-3 px-4 text-[#6B6862] max-w-xs truncate">
                      {file.notes || '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        <a
                          href={api.getFileUrl(file.id)}
                          download={file.original_filename}
                          className="p-1 text-[#6B6862] hover:text-[#0F766E] rounded hover:bg-stone-100"
                          title="Download original file"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                        <button
                          onClick={() => setDeleteTarget(file)}
                          className="p-1 text-[#9C9890] hover:text-rose-600 rounded hover:bg-stone-100"
                          title="Delete evidence"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
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

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleConfirmDelete}
        title="Delete evidence file?"
        message={`This will permanently remove "${deleteTarget?.original_filename}" from the database and disk storage.`}
      />
    </div>
  );
};
