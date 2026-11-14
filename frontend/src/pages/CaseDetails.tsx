import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, Trash2, Download, Copy, Check } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { EvidenceFile } from '../types';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const CaseDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { cases, deleteCase, deleteEvidence, setActiveCaseId } = useApp();

  const [caseEvidence, setCaseEvidence] = useState<EvidenceFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [deleteEvidenceTarget, setDeleteEvidenceTarget] = useState<EvidenceFile | null>(null);
  const [isDeleteCaseOpen, setIsDeleteCaseOpen] = useState<boolean>(false);

  const currentCase = cases.find((c) => c.id === id);

  const loadCaseFiles = async () => {
    if (!id) return;
    try {
      setIsLoadingFiles(true);
      const files = await api.getCaseEvidence(id);
      setCaseEvidence(files);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  useEffect(() => {
    loadCaseFiles();
    if (id) setActiveCaseId(id);
  }, [id]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const handleCopyHash = (hash: string, fileId: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(fileId);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleConfirmDeleteEvidence = async () => {
    if (deleteEvidenceTarget) {
      await deleteEvidence(deleteEvidenceTarget.id);
      setDeleteEvidenceTarget(null);
      await loadCaseFiles();
    }
  };

  const handleConfirmDeleteCase = async () => {
    if (id) {
      await deleteCase(id);
      navigate('/cases');
    }
  };

  if (!currentCase) {
    return (
      <div className="py-12 text-center max-w-sm mx-auto">
        <h2 className="text-sm font-semibold text-[#1C1917] mb-1">Case not found</h2>
        <p className="text-xs text-[#6B6862] mb-4">This case ID does not exist in the database.</p>
        <Button variant="secondary" size="sm" onClick={() => navigate('/cases')}>
          Back to cases
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button and Case Header */}
      <div>
        <button
          onClick={() => navigate('/cases')}
          className="inline-flex items-center gap-1.5 text-xs text-[#6B6862] hover:text-[#1C1917] mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to cases
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E6E4DF]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-[#6B6862]">Case</span>
              <span className="font-mono text-xs font-semibold text-[#1C1917] bg-[#F5F5F0] px-1.5 py-0.5 rounded">
                {currentCase.id}
              </span>
            </div>
            <p className="text-xs text-[#6B6862]">
              Created {new Date(currentCase.created_at).toLocaleString()} • {caseEvidence.length} file{caseEvidence.length === 1 ? '' : 's'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/upload')}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Add evidence</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsDeleteCaseOpen(true)}
              className="text-rose-600 hover:bg-rose-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete case</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Evidence Table */}
      {isLoadingFiles ? (
        <div className="py-12 text-center text-xs text-[#6B6862]">Loading evidence files...</div>
      ) : caseEvidence.length === 0 ? (
        <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-6">
          <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No evidence in this case yet</h3>
          <p className="text-xs text-[#6B6862] mb-4">
            Upload images, voice recordings, or chat logs to preserve them under this case.
          </p>
          <Button variant="primary" size="sm" onClick={() => navigate('/upload')}>
            Add evidence to this case
          </Button>
        </div>
      ) : (
        <div className="bg-white border border-[#E6E4DF] rounded-md overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#E6E4DF] bg-[#F9F9F7] text-[#6B6862]">
                <th className="py-2.5 px-4 font-medium">Filename</th>
                <th className="py-2.5 px-4 font-medium">Type</th>
                <th className="py-2.5 px-4 font-medium">Size</th>
                <th className="py-2.5 px-4 font-medium">SHA-256 hash</th>
                <th className="py-2.5 px-4 font-medium">Notes</th>
                <th className="py-2.5 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E6E4DF]">
              {caseEvidence.map((file) => {
                const truncatedHash = `${file.sha256.substring(0, 8)}...${file.sha256.substring(file.sha256.length - 6)}`;
                const isCopied = copiedHash === file.id;

                return (
                  <tr key={file.id} className="hover:bg-[#F9F9F7] transition-colors">
                    <td className="py-3 px-4 font-medium text-[#1C1917] max-w-xs truncate" title={file.original_filename}>
                      {file.original_filename}
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
                          onClick={() => setDeleteEvidenceTarget(file)}
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

      {/* Delete Evidence Confirmation */}
      <ConfirmDialog
        isOpen={deleteEvidenceTarget !== null}
        onClose={() => setDeleteEvidenceTarget(null)}
        onConfirm={handleConfirmDeleteEvidence}
        title="Delete evidence file?"
        message={`This will delete "${deleteEvidenceTarget?.original_filename}" from this case.`}
      />

      {/* Delete Case Confirmation */}
      <ConfirmDialog
        isOpen={isDeleteCaseOpen}
        onClose={() => setIsDeleteCaseOpen(false)}
        onConfirm={handleConfirmDeleteCase}
        title="Delete this case?"
        message="This will delete this case and all evidence files associated with it."
      />
    </div>
  );
};
