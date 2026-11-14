import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Briefcase, 
  ArrowLeft, 
  UploadCloud, 
  Plus, 
  FileCheck, 
  FileText, 
  Clock, 
  Trash2, 
  Edit3, 
  Calendar, 
  Tag, 
  Share2, 
  Copy, 
  Check,
  FolderLock
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { CaseStatusBadge, EvidenceTypeBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { CaseNote } from '../types';

export const CaseDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { cases, evidence, activities, addCaseNote, updateCaseNote, deleteCaseNote, deleteCase } = useApp();

  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'notes' | 'activity'>('overview');
  const [copiedId, setCopiedId] = useState<boolean>(false);

  // Note modal states
  const [isNoteModalOpen, setIsNoteModalOpen] = useState<boolean>(false);
  const [editingNote, setEditingNote] = useState<CaseNote | null>(null);
  const [noteTitle, setNoteTitle] = useState<string>('');
  const [noteContent, setNoteContent] = useState<string>('');
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [isDeleteCaseOpen, setIsDeleteCaseOpen] = useState<boolean>(false);

  const currentCase = cases.find((c) => c.id === id);

  if (!currentCase) {
    return (
      <div className="text-center py-20 bg-[#162032] border border-slate-800 rounded-2xl">
        <Briefcase className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h2 className="text-base font-semibold text-white mb-2">Case Not Found</h2>
        <p className="text-xs text-slate-400 mb-4">The case ID "{id}" does not exist or has been deleted.</p>
        <Button variant="primary" size="sm" onClick={() => navigate('/cases')}>
          Return to Cases
        </Button>
      </div>
    );
  }

  const caseEvidence = evidence.filter((e) => e.caseId === currentCase.id);
  const caseActivities = activities.filter((a) => a.caseId === currentCase.id);

  const handleCopyId = () => {
    navigator.clipboard.writeText(currentCase.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleOpenAddNote = () => {
    setEditingNote(null);
    setNoteTitle('');
    setNoteContent('');
    setIsNoteModalOpen(true);
  };

  const handleOpenEditNote = (note: CaseNote) => {
    setEditingNote(note);
    setNoteTitle(note.title);
    setNoteContent(note.content);
    setIsNoteModalOpen(true);
  };

  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteTitle.trim()) return;

    if (editingNote) {
      await updateCaseNote(currentCase.id, editingNote.id, {
        title: noteTitle.trim(),
        content: noteContent.trim()
      });
    } else {
      await addCaseNote(currentCase.id, noteTitle.trim(), noteContent.trim());
    }

    setIsNoteModalOpen(false);
  };

  const handleConfirmDeleteNote = async () => {
    if (deleteNoteId) {
      await deleteCaseNote(currentCase.id, deleteNoteId);
      setDeleteNoteId(null);
    }
  };

  const handleConfirmDeleteCase = async () => {
    await deleteCase(currentCase.id);
    navigate('/cases');
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Navigation Back Link & Header */}
      <div>
        <button
          onClick={() => navigate('/cases')}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-4 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Cases
        </button>

        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs font-mono font-bold text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded border border-blue-500/20">
                {currentCase.id}
              </span>
              <CaseStatusBadge status={currentCase.status} />
              {currentCase.priority && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  Priority: {currentCase.priority}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{currentCase.title}</h1>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">{currentCase.description}</p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={handleCopyId}
              className="p-2 rounded-xl text-slate-400 hover:text-white bg-[#162032] border border-slate-700 transition-colors"
              title="Copy Case ID"
            >
              {copiedId ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
            <Button variant="cyan" size="sm" onClick={() => navigate('/upload')}>
              <UploadCloud className="w-4 h-4" />
              <span>Add Evidence</span>
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setIsDeleteCaseOpen(true)} className="text-rose-400 hover:bg-rose-500/10">
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'evidence', label: `Evidence (${caseEvidence.length})` },
          { key: 'notes', label: `Investigative Notes (${currentCase.notes?.length || 0})` },
          { key: 'activity', label: `Activity (${caseActivities.length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-all ${
              activeTab === tab.key
                ? 'border-blue-500 text-blue-400 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">Case Summary</h3>
              <p className="text-xs text-slate-300 leading-relaxed mb-4">
                {currentCase.description}
              </p>

              {currentCase.tags && currentCase.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-800">
                  {currentCase.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="text-[11px] font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white">Recent Evidence in this Case</h3>
                <Button variant="ghost" size="sm" onClick={() => setActiveTab('evidence')} className="text-xs text-blue-400">
                  View all ({caseEvidence.length}) →
                </Button>
              </div>

              {caseEvidence.length === 0 ? (
                <div className="text-center py-6 text-slate-400 text-xs">
                  No evidence uploaded yet for this case.
                </div>
              ) : (
                <div className="space-y-2">
                  {caseEvidence.slice(0, 3).map((file) => (
                    <div
                      key={file.id}
                      onClick={() => navigate(`/vault/${file.id}`)}
                      className="p-3 rounded-xl bg-slate-800/40 border border-slate-800 hover:border-slate-700 transition-colors flex items-center justify-between cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5">
                        <EvidenceTypeBadge type={file.fileType} />
                        <span className="text-xs text-white font-medium">{file.displayName}</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">
                        {new Date(file.dateAdded).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Case Metadata Info */}
          <div className="space-y-4">
            <div className="bg-[#162032] border border-slate-800 rounded-2xl p-5 space-y-3.5">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
                Case Metadata
              </h3>
              <div>
                <span className="text-[11px] text-slate-400 block">Case UUID</span>
                <span className="text-xs font-mono text-white font-medium select-all">{currentCase.id}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Status</span>
                <span className="text-xs font-medium text-white">{currentCase.status}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Date Created</span>
                <span className="text-xs font-mono text-white">
                  {new Date(currentCase.createdAt).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Last Modified</span>
                <span className="text-xs font-mono text-white">
                  {new Date(currentCase.updatedAt).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Evidence */}
      {activeTab === 'evidence' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-[#162032] border border-slate-800 rounded-xl p-3">
            <span className="text-xs font-medium text-slate-300">
              Showing {caseEvidence.length} items preserved under case [{currentCase.id}]
            </span>
            <Button variant="cyan" size="sm" onClick={() => navigate('/upload')}>
              <UploadCloud className="w-3.5 h-3.5" />
              Upload to Case
            </Button>
          </div>

          {caseEvidence.length === 0 ? (
            <div className="text-center py-16 bg-[#162032] border border-slate-800 rounded-2xl">
              <FolderLock className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white mb-1">No evidence items in this case yet</h3>
              <p className="text-xs text-slate-400 mb-4">Upload screenshots, recordings, or chat logs to preserve chain of custody.</p>
              <Button variant="primary" size="sm" onClick={() => navigate('/upload')}>
                Upload Evidence
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {caseEvidence.map((item) => (
                <div
                  key={item.id}
                  onClick={() => navigate(`/vault/${item.id}`)}
                  className="bg-[#162032] border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <EvidenceTypeBadge type={item.fileType} />
                    <span className="text-[11px] font-mono text-slate-400">{item.id}</span>
                  </div>
                  <h4 className="text-xs font-semibold text-white truncate group-hover:text-blue-400 transition-colors mb-1">
                    {item.displayName}
                  </h4>
                  <p className="text-[11px] font-mono text-slate-400 truncate mb-3">{item.fileName}</p>
                  <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800 flex justify-between">
                    <span>{(item.fileSize / 1024).toFixed(1)} KB</span>
                    <span>{new Date(item.dateAdded).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Notes */}
      {activeTab === 'notes' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              Document client statements, investigation logs, and timeline cross-references.
            </span>
            <Button variant="primary" size="sm" onClick={handleOpenAddNote}>
              <Plus className="w-3.5 h-3.5" />
              <span>Add Note</span>
            </Button>
          </div>

          {!currentCase.notes || currentCase.notes.length === 0 ? (
            <div className="text-center py-16 bg-[#162032] border border-slate-800 rounded-2xl">
              <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white mb-1">No notes recorded yet</h3>
              <p className="text-xs text-slate-400 mb-4">Add case notes, timeline confirmations, and legal observations.</p>
              <Button variant="primary" size="sm" onClick={handleOpenAddNote}>
                + Add First Note
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentCase.notes.map((note) => (
                <div
                  key={note.id}
                  className="bg-[#162032] border border-slate-800 rounded-xl p-5 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-semibold text-white">{note.title}</h4>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleOpenEditNote(note)}
                          className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setDeleteNoteId(note.id)}
                          className="p-1 text-slate-400 hover:text-rose-400 rounded hover:bg-rose-500/10"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line mb-4">
                      {note.content}
                    </p>
                  </div>
                  <div className="text-[11px] font-mono text-slate-400 pt-3 border-t border-slate-800">
                    Created {new Date(note.createdAt).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Activity */}
      {activeTab === 'activity' && (
        <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4">Case Action History</h3>
          {caseActivities.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-xs">No activity logged for this case.</div>
          ) : (
            <div className="relative pl-6 border-l border-slate-800 space-y-6">
              {caseActivities.map((act) => (
                <div key={act.id} className="relative">
                  <span className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-blue-500 ring-4 ring-[#162032]" />
                  <div>
                    <p className="text-xs font-medium text-slate-200">{act.description}</p>
                    <span className="text-[10px] font-mono text-slate-400 mt-1 block">
                      {new Date(act.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add / Edit Note Modal */}
      <Modal
        isOpen={isNoteModalOpen}
        onClose={() => setIsNoteModalOpen(false)}
        title={editingNote ? 'Edit Investigative Note' : 'Add Case Note'}
        maxWidth="md"
      >
        <form onSubmit={handleSaveNote} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Note Title *</label>
            <input
              type="text"
              required
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
              placeholder="e.g. Chain of Custody Intake Check"
              className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Note Content *</label>
            <textarea
              rows={5}
              required
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Record testimony observations, device serial numbers, or timeline details..."
              className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>

          <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-800">
            <Button type="button" variant="outline" size="sm" onClick={() => setIsNoteModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm">
              {editingNote ? 'Save Note' : 'Add Note'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Note Confirmation */}
      <ConfirmDialog
        isOpen={deleteNoteId !== null}
        onClose={() => setDeleteNoteId(null)}
        onConfirm={handleConfirmDeleteNote}
        title="Delete Note?"
        message="Are you sure you want to delete this case note? This action cannot be undone."
      />

      {/* Delete Case Confirmation */}
      <ConfirmDialog
        isOpen={isDeleteCaseOpen}
        onClose={() => setIsDeleteCaseOpen(false)}
        onConfirm={handleConfirmDeleteCase}
        title={`Delete Case [${currentCase.id}]?`}
        message="This will permanently delete this case and remove all associated evidence files."
      />
    </div>
  );
};
