import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Upload, Trash2, Download, Copy, Check, Zap,
  Users, FileText, CheckCircle2, XCircle, AlertCircle,
  Eye, RefreshCw, Layers, ShieldCheck, UserCheck, UserX, Split
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { EvidenceFile, CandidateMatch } from '../types';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { Modal } from '../components/common/Modal';

export const CaseDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { cases, deleteCase, deleteEvidence, setActiveCaseId } = useApp();

  const [activeTab, setActiveTab] = useState<'evidence' | 'entities'>('evidence');
  const [caseEvidence, setCaseEvidence] = useState<EvidenceFile[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [deleteEvidenceTarget, setDeleteEvidenceTarget] = useState<EvidenceFile | null>(null);
  const [isDeleteCaseOpen, setIsDeleteCaseOpen] = useState<boolean>(false);

  // Extraction states
  const [extractingIds, setExtractingIds] = useState<Set<string>>(new Set());
  const [isExtractingAll, setIsExtractingAll] = useState<boolean>(false);
  const [viewingEvidence, setViewingEvidence] = useState<EvidenceFile | null>(null);

  // Entity matching states
  const [candidateMatches, setCandidateMatches] = useState<CandidateMatch[]>([]);
  const [isLoadingEntities, setIsLoadingEntities] = useState<boolean>(false);
  const [isMatchingEntities, setIsMatchingEntities] = useState<boolean>(false);
  const [entityFilter, setEntityFilter] = useState<string>('all');
  const [reviewingMatchId, setReviewingMatchId] = useState<string | null>(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const currentCase = cases.find((c) => c.id === id);

  const loadCaseFiles = async () => {
    if (!id) return;
    try {
      setIsLoadingFiles(true);
      const files = await api.getCaseEvidence(id);
      setCaseEvidence(files);
    } catch (err) {
      console.error('Failed to load case evidence', err);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  const loadEntities = async () => {
    if (!id) return;
    try {
      setIsLoadingEntities(true);
      const matches = await api.getCaseEntities(id);
      setCandidateMatches(matches);
    } catch (err) {
      console.error('Failed to load entities', err);
    } finally {
      setIsLoadingEntities(false);
    }
  };

  useEffect(() => {
    loadCaseFiles();
    loadEntities();
    if (id) setActiveCaseId(id);
  }, [id]);

  const showNotification = (msg: string) => {
    setActionSuccessMsg(msg);
    setTimeout(() => setActionSuccessMsg(null), 3500);
  };

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

  // Run Extraction on single file
  const handleExtractSingle = async (file: EvidenceFile) => {
    setExtractingIds((prev) => new Set(prev).add(file.id));
    try {
      const updated = await api.triggerExtraction(file.id);
      setCaseEvidence((prev) =>
        prev.map((f) => (f.id === file.id ? { ...f, ...updated } : f))
      );
      if (viewingEvidence?.id === file.id) {
        setViewingEvidence((prev) => (prev ? { ...prev, ...updated } : null));
      }
      showNotification(`Extracted intelligence from "${file.original_filename}"`);
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setExtractingIds((prev) => {
        const next = new Set(prev);
        next.delete(file.id);
        return next;
      });
    }
  };

  // Run Batch Extraction on all files in case
  const handleExtractAll = async () => {
    if (!id) return;
    setIsExtractingAll(true);
    try {
      const updated = await api.extractAllCaseEvidence(id);
      setCaseEvidence(updated);
      showNotification(`Batch extraction completed for ${updated.length} file(s).`);
    } catch (err: any) {
      alert(`Batch extraction failed: ${err.message}`);
    } finally {
      setIsExtractingAll(false);
    }
  };

  // Run Cross-Evidence Entity Extraction & Matching
  const handleMatchEntities = async () => {
    if (!id) return;
    setIsMatchingEntities(true);
    try {
      const matches = await api.matchCaseEntities(id);
      setCandidateMatches(matches);
      setActiveTab('entities');
      showNotification(`Entity intelligence completed. Found ${matches.length} candidate clusters.`);
    } catch (err: any) {
      alert(`Entity analysis failed: ${err.message}`);
    } finally {
      setIsMatchingEntities(false);
    }
  };

  // Review Candidate Match
  const handleReviewMatch = async (matchId: string, action: 'confirm' | 'reject' | 'separate' | 'undo') => {
    setReviewingMatchId(matchId);
    try {
      const updated = await api.reviewEntityMatch(matchId, action);
      setCandidateMatches((prev) =>
        prev.map((m) => (m.id === matchId ? updated : m))
      );
      const actionLabels = {
        confirm: 'Identity match confirmed',
        reject: 'Match rejected',
        separate: 'Entities marked as separate individuals',
        undo: 'Review decision reset to pending'
      };
      showNotification(actionLabels[action]);
    } catch (err: any) {
      alert(`Review action failed: ${err.message}`);
    } finally {
      setReviewingMatchId(null);
    }
  };

  const filteredMatches = candidateMatches.filter((m) => {
    if (entityFilter === 'all') return true;
    return m.entity_type.toLowerCase() === entityFilter.toLowerCase();
  });

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
      {/* Toast Notification */}
      {actionSuccessMsg && (
        <div className="fixed top-4 right-4 z-50 bg-[#1C1917] text-white text-xs px-3.5 py-2.5 rounded shadow-lg flex items-center gap-2 border border-stone-700 animate-fade-in">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#2DD4BF]" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* Header and Controls */}
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

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExtractAll}
              disabled={isExtractingAll || caseEvidence.length === 0}
              title="Run extraction across all files in this case"
            >
              <Zap className={`w-3.5 h-3.5 text-amber-600 ${isExtractingAll ? 'animate-spin' : ''}`} />
              <span>{isExtractingAll ? 'Extracting All...' : 'Extract All'}</span>
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleMatchEntities}
              disabled={isMatchingEntities || caseEvidence.length === 0}
              className="text-[#0F766E] border-[#0F766E]/30 hover:bg-[#0F766E]/5"
              title="Detect and match entities across all evidence using GLiNER + RapidFuzz"
            >
              <Users className={`w-3.5 h-3.5 ${isMatchingEntities ? 'animate-pulse' : ''}`} />
              <span>{isMatchingEntities ? 'Matching...' : 'Match Entities'}</span>
            </Button>

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
            </Button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-4 border-b border-[#E6E4DF] text-xs font-medium">
        <button
          onClick={() => setActiveTab('evidence')}
          className={`pb-2.5 inline-flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'evidence'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Evidence Files ({caseEvidence.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('entities')}
          className={`pb-2.5 inline-flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'entities'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#6B6862] hover:text-[#1C1917]'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Entity Intelligence & Matching ({candidateMatches.length})</span>
        </button>
      </div>

      {/* TAB 1: Evidence Files & Intelligence */}
      {activeTab === 'evidence' && (
        <div>
          {isLoadingFiles ? (
            <div className="py-12 text-center text-xs text-[#6B6862]">Loading evidence files...</div>
          ) : caseEvidence.length === 0 ? (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-6">
              <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No evidence in this case yet</h3>
              <p className="text-xs text-[#6B6862] mb-4">
                Upload images, audio recordings, PDFs, DOCX, or chat logs to preserve and analyze them.
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
                    <th className="py-2.5 px-4 font-medium">SHA-256</th>
                    <th className="py-2.5 px-4 font-medium">Extraction Status</th>
                    <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6E4DF]">
                  {caseEvidence.map((file) => {
                    const truncatedHash = `${file.sha256.substring(0, 8)}...${file.sha256.substring(file.sha256.length - 6)}`;
                    const isCopied = copiedHash === file.id;
                    const isExtracting = extractingIds.has(file.id);
                    const hasExtractedText = Boolean(file.extracted_text && file.extracted_text.trim());

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

                        {/* Extraction Status & Quick View */}
                        <td className="py-3 px-4">
                          {isExtracting ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] bg-amber-50 text-amber-700 font-medium animate-pulse">
                              <RefreshCw className="w-3 h-3 animate-spin" />
                              Extracting...
                            </span>
                          ) : hasExtractedText ? (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setViewingEvidence(file)}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200 transition-colors font-medium"
                                title="Click to view full extracted text and metadata"
                              >
                                <Eye className="w-3 h-3 text-emerald-600" />
                                <span>{(file.extraction_confidence ? (file.extraction_confidence * 100).toFixed(1) : 100)}% conf</span>
                                {file.processing_time_ms && (
                                  <span className="text-emerald-700 font-mono text-[10px]">
                                    ({Math.round(file.processing_time_ms)}ms)
                                  </span>
                                )}
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => handleExtractSingle(file)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-stone-100 text-stone-700 hover:bg-stone-200 border border-stone-200 transition-colors font-medium"
                            >
                              <Zap className="w-3 h-3 text-amber-600" />
                              <span>Extract</span>
                            </button>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center gap-1.5">
                            {hasExtractedText && (
                              <button
                                onClick={() => setViewingEvidence(file)}
                                className="p-1 text-[#6B6862] hover:text-[#0F766E] rounded hover:bg-stone-100"
                                title="View extracted text"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                            )}
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
        </div>
      )}

      {/* TAB 2: Entity Intelligence & Disambiguation */}
      {activeTab === 'entities' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F9F9F7] p-3 rounded-md border border-[#E6E4DF]">
            <div>
              <h3 className="text-xs font-semibold text-[#1C1917]">Cross-Evidence Entity Intelligence</h3>
              <p className="text-[11px] text-[#6B6862]">
                GLiNER extracted entities grouped with RapidFuzz similarity scoring. Review and confirm matches below.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handleMatchEntities}
                disabled={isMatchingEntities}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isMatchingEntities ? 'animate-spin' : ''}`} />
                <span>{isMatchingEntities ? 'Analyzing...' : 'Re-run Analysis'}</span>
              </Button>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            {['all', 'person', 'organization', 'location', 'date', 'identifier'].map((filterKey) => (
              <button
                key={filterKey}
                onClick={() => setEntityFilter(filterKey)}
                className={`px-2.5 py-1 rounded text-xs capitalize transition-colors font-medium ${
                  entityFilter === filterKey
                    ? 'bg-[#0F766E] text-white'
                    : 'bg-white border border-[#E6E4DF] text-[#6B6862] hover:text-[#1C1917]'
                }`}
              >
                {filterKey === 'all' ? `All (${candidateMatches.length})` : filterKey}
              </button>
            ))}
          </div>

          {/* Candidate Matches List */}
          {isLoadingEntities ? (
            <div className="py-12 text-center text-xs text-[#6B6862]">Loading entity intelligence...</div>
          ) : filteredMatches.length === 0 ? (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-6">
              <Users className="w-8 h-8 text-[#9C9890] mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No entity matches found</h3>
              <p className="text-xs text-[#6B6862] mb-4">
                Click "Match Entities" to run GLiNER and RapidFuzz across your case evidence.
              </p>
              <Button variant="primary" size="sm" onClick={handleMatchEntities} disabled={isMatchingEntities}>
                Detect & Match Entities
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredMatches.map((cand) => {
                const isReviewing = reviewingMatchId === cand.id;
                const distinctFiles = Array.from(new Set(cand.mentions.map((m) => m.filename)));

                return (
                  <div
                    key={cand.id}
                    className={`bg-white border rounded-md p-4 space-y-3 transition-shadow ${
                      cand.status === 'confirmed'
                        ? 'border-emerald-300 ring-1 ring-emerald-200'
                        : cand.status === 'rejected'
                        ? 'border-rose-200 opacity-75'
                        : cand.status === 'separate'
                        ? 'border-stone-300'
                        : 'border-[#E6E4DF] hover:shadow-sm'
                    }`}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-[#1C1917]">
                            {cand.canonical_name}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-stone-100 text-stone-600">
                            {cand.entity_type}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#6B6862] mt-0.5">
                          Found across {distinctFiles.length} evidence file{distinctFiles.length === 1 ? '' : 's'} ({cand.mentions.length} mention{cand.mentions.length === 1 ? '' : 's'})
                        </div>
                      </div>

                      {/* Similarity & Status Badge */}
                      <div className="flex flex-col items-end gap-1">
                        <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                          {cand.similarity_score}% similarity
                        </span>
                        {cand.status === 'confirmed' && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                            <CheckCircle2 className="w-3 h-3" /> Confirmed
                          </span>
                        )}
                        {cand.status === 'rejected' && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-rose-600 font-medium">
                            <XCircle className="w-3 h-3" /> Rejected
                          </span>
                        )}
                        {cand.status === 'separate' && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-stone-600 font-medium">
                            <Split className="w-3 h-3" /> Separate
                          </span>
                        )}
                        {cand.status === 'pending' && (
                          <span className="text-[11px] text-amber-700 font-medium">
                            Pending Review
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Mentions Provenance */}
                    <div className="bg-[#F9F9F7] rounded p-2.5 text-xs space-y-1.5 border border-[#E6E4DF]">
                      <div className="text-[10px] uppercase font-semibold text-[#9C9890] tracking-wider">
                        Source Mentions & Provenance:
                      </div>
                      {cand.mentions.map((m, mIdx) => (
                        <div key={mIdx} className="flex items-center justify-between text-[11px] gap-2">
                          <span className="font-medium text-[#1C1917] truncate max-w-[200px]">
                            "{m.text}"
                          </span>
                          <div className="flex items-center gap-1 text-[#6B6862]">
                            <a
                              href={api.getFileUrl(m.evidence_id)}
                              download={m.filename}
                              className="hover:text-[#0F766E] underline truncate max-w-[140px]"
                              title={`Download original file: ${m.filename}`}
                            >
                              {m.filename}
                            </a>
                            <span className="text-[10px] font-mono text-[#9C9890]">
                              ({Math.round(m.confidence * 100)}%)
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Review Controls */}
                    <div className="pt-2 border-t border-[#E6E4DF] flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleReviewMatch(cand.id, 'confirm')}
                          disabled={isReviewing || cand.status === 'confirmed'}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            cand.status === 'confirmed'
                              ? 'bg-emerald-600 text-white cursor-default'
                              : 'bg-white border border-[#E6E4DF] text-emerald-700 hover:bg-emerald-50'
                          }`}
                          title="Confirm that these mentions correspond to the same individual or entity"
                        >
                          <UserCheck className="w-3.5 h-3.5" />
                          <span>Confirm</span>
                        </button>

                        <button
                          onClick={() => handleReviewMatch(cand.id, 'separate')}
                          disabled={isReviewing || cand.status === 'separate'}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            cand.status === 'separate'
                              ? 'bg-stone-600 text-white cursor-default'
                              : 'bg-white border border-[#E6E4DF] text-stone-700 hover:bg-stone-100'
                          }`}
                          title="Explicitly mark these mentions as distinct separate individuals"
                        >
                          <Split className="w-3.5 h-3.5" />
                          <span>Separate</span>
                        </button>

                        <button
                          onClick={() => handleReviewMatch(cand.id, 'reject')}
                          disabled={isReviewing || cand.status === 'rejected'}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            cand.status === 'rejected'
                              ? 'bg-rose-600 text-white cursor-default'
                              : 'bg-white border border-[#E6E4DF] text-rose-700 hover:bg-rose-50'
                          }`}
                          title="Reject false candidate match"
                        >
                          <UserX className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </div>

                      {cand.status !== 'pending' && (
                        <button
                          onClick={() => handleReviewMatch(cand.id, 'undo')}
                          disabled={isReviewing}
                          className="text-[11px] text-[#6B6862] hover:text-[#1C1917] underline"
                        >
                          Reset
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Extracted Intelligence Inspection Modal */}
      {viewingEvidence && (
        <Modal
          isOpen={true}
          onClose={() => setViewingEvidence(null)}
          title={`Extracted Intelligence — ${viewingEvidence.original_filename}`}
        >
          <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
            {/* Metadata Badges */}
            <div className="flex flex-wrap items-center gap-2 p-2.5 bg-[#F9F9F7] rounded border border-[#E6E4DF] text-xs">
              <span className="font-medium text-[#1C1917]">Confidence:</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold font-mono text-[11px]">
                {((viewingEvidence.extraction_confidence ?? 1.0) * 100).toFixed(1)}%
              </span>

              {viewingEvidence.processing_time_ms && (
                <>
                  <span className="text-[#9C9890]">•</span>
                  <span className="font-medium text-[#1C1917]">Processing Time:</span>
                  <span className="font-mono text-stone-700">
                    {Math.round(viewingEvidence.processing_time_ms)} ms
                  </span>
                </>
              )}

              <span className="text-[#9C9890]">•</span>
              <span className="font-medium text-[#1C1917]">Type:</span>
              <span className="uppercase font-mono text-stone-700">{viewingEvidence.file_type}</span>

              <div className="ml-auto">
                <a
                  href={api.getFileUrl(viewingEvidence.id)}
                  download={viewingEvidence.original_filename}
                  className="inline-flex items-center gap-1 text-[11px] text-[#0F766E] hover:underline"
                >
                  <Download className="w-3 h-3" />
                  <span>Download original</span>
                </a>
              </div>
            </div>

            {/* Extracted Text Content */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-[#6B6862]">
                <span className="font-medium text-[#1C1917]">Full Extracted Text:</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(viewingEvidence.extracted_text || '');
                    showNotification('Copied extracted text to clipboard');
                  }}
                  className="inline-flex items-center gap-1 hover:text-[#1C1917]"
                >
                  <Copy className="w-3 h-3" />
                  <span>Copy text</span>
                </button>
              </div>

              <div className="bg-stone-50 border border-[#E6E4DF] rounded p-3 font-mono text-xs whitespace-pre-wrap text-[#1C1917] max-h-80 overflow-y-auto leading-relaxed">
                {viewingEvidence.extracted_text || 'No text extracted from this file.'}
              </div>
            </div>

            {/* Re-run button */}
            <div className="flex justify-end gap-2 pt-2 border-t border-[#E6E4DF]">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleExtractSingle(viewingEvidence)}
                disabled={extractingIds.has(viewingEvidence.id)}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${extractingIds.has(viewingEvidence.id) ? 'animate-spin' : ''}`} />
                <span>Re-run Extraction</span>
              </Button>
              <Button variant="primary" size="sm" onClick={() => setViewingEvidence(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
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
