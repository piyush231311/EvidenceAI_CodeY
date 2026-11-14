import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Briefcase, 
  Plus, 
  Search, 
  Filter, 
  Calendar, 
  Trash2, 
  Edit3, 
  ExternalLink,
  Tag,
  ArrowUpDown
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Case, CaseStatus } from '../types';
import { CaseStatusBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const Cases: React.FC = () => {
  const navigate = useNavigate();
  const { cases, createCase, updateCase, deleteCase } = useApp();

  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'date' | 'title' | 'evidence'>('date');

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [editCase, setEditCase] = useState<Case | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Case | null>(null);

  // Form states
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'Active' as CaseStatus,
    priority: 'Medium' as 'Low' | 'Medium' | 'High' | 'Critical',
    tags: ''
  });

  const handleOpenCreate = () => {
    setFormData({
      title: '',
      description: '',
      status: 'Active',
      priority: 'High',
      tags: 'Intake, Digital Evidence'
    });
    setIsCreateOpen(true);
  };

  const handleOpenEdit = (c: Case, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditCase(c);
    setFormData({
      title: c.title,
      description: c.description,
      status: c.status,
      priority: c.priority || 'Medium',
      tags: c.tags ? c.tags.join(', ') : ''
    });
  };

  const handleSubmitCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return;

    await createCase({
      title: formData.title.trim(),
      description: formData.description.trim(),
      status: formData.status,
      priority: formData.priority,
      tags: formData.tags.split(',').map((t) => t.trim()).filter(Boolean)
    });

    setIsCreateOpen(false);
  };

  const handleSubmitEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editCase || !formData.title.trim()) return;

    await updateCase(editCase.id, {
      title: formData.title.trim(),
      description: formData.description.trim(),
      status: formData.status,
      priority: formData.priority,
      tags: formData.tags.split(',').map((t) => t.trim()).filter(Boolean)
    });

    setEditCase(null);
  };

  const handleConfirmDelete = async () => {
    if (deleteTarget) {
      await deleteCase(deleteTarget.id);
      setDeleteTarget(null);
    }
  };

  // Filter and sort
  const filteredCases = cases
    .filter((c) => {
      const matchesSearch = 
        c.title.toLowerCase().includes(search.toLowerCase()) ||
        c.description.toLowerCase().includes(search.toLowerCase()) ||
        c.id.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === 'All' || c.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      if (sortBy === 'date') return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      if (sortBy === 'title') return a.title.localeCompare(b.title);
      if (sortBy === 'evidence') return (b.evidenceCount || 0) - (a.evidenceCount || 0);
      return 0;
    });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Briefcase className="w-6 h-6 text-blue-400" />
            Case Management
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Create, organize, and monitor sensitive digital investigation cases and chains-of-custody.
          </p>
        </div>

        <Button variant="primary" onClick={handleOpenCreate}>
          <Plus className="w-4 h-4" />
          <span>New Case</span>
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-[#162032] border border-slate-800 rounded-xl p-3">
        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            placeholder="Search cases by ID or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#0F172A] border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2.5 w-full md:w-auto justify-end">
          <div className="flex items-center gap-1.5 bg-[#0F172A] border border-slate-700 rounded-lg px-2.5 py-1">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-[#162032]">All Statuses</option>
              <option value="Active" className="bg-[#162032]">Active</option>
              <option value="Under Review" className="bg-[#162032]">Under Review</option>
              <option value="Archived" className="bg-[#162032]">Archived</option>
              <option value="Closed" className="bg-[#162032]">Closed</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-[#0F172A] border border-slate-700 rounded-lg px-2.5 py-1">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer"
            >
              <option value="date" className="bg-[#162032]">Sort by Recent</option>
              <option value="title" className="bg-[#162032]">Sort by Title</option>
              <option value="evidence" className="bg-[#162032]">Sort by Evidence</option>
            </select>
          </div>
        </div>
      </div>

      {/* Cases Grid */}
      {filteredCases.length === 0 ? (
        <div className="bg-[#162032] border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
          <Briefcase className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-white mb-1">No cases match your filters</h3>
          <p className="text-xs text-slate-400 mb-4">Try adjusting your search terms or create a new investigation case.</p>
          <Button variant="primary" size="sm" onClick={handleOpenCreate}>
            + Create New Case
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCases.map((c) => (
            <div
              key={c.id}
              onClick={() => navigate(`/cases/${c.id}`)}
              className="bg-[#162032] border border-slate-800 hover:border-slate-700 rounded-2xl p-5 transition-all duration-200 hover:-translate-y-0.5 cursor-pointer flex flex-col justify-between group shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="text-xs font-mono font-semibold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                    {c.id}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <CaseStatusBadge status={c.status} />
                  </div>
                </div>

                <h3 className="text-base font-semibold text-white group-hover:text-blue-400 transition-colors mb-2 leading-snug">
                  {c.title}
                </h3>
                <p className="text-xs text-slate-400 line-clamp-3 mb-4 leading-relaxed">
                  {c.description}
                </p>

                {c.tags && c.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {c.tags.map((t, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60"
                      >
                        #{t}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-800/80">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
                  <span className="font-mono text-slate-300 font-medium">
                    {c.evidenceCount || 0} evidence item(s)
                  </span>
                  <span className="text-[11px] font-mono">
                    Updated {new Date(c.updatedAt).toLocaleDateString()}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => handleOpenEdit(c, e)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                      title="Edit case"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(c);
                      }}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                      title="Delete case"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <span className="text-xs text-blue-400 font-medium flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                    Workspace <ExternalLink className="w-3 h-3" />
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Case Modal */}
      <Modal
        isOpen={isCreateOpen || editCase !== null}
        onClose={() => {
          setIsCreateOpen(false);
          setEditCase(null);
        }}
        title={editCase ? `Edit Case [${editCase.id}]` : 'Create New Investigation Case'}
        description="Cases group all related digital evidence, notes, and cryptographic chain-of-custody records."
        maxWidth="md"
      >
        <form onSubmit={editCase ? handleSubmitEdit : handleSubmitCreate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Case Title *
            </label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g. Workplace Intimidation & Source Defamation"
              className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Case Description & Background
            </label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Summary of incident, key dates, suspected parties, or legal context..."
              className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Investigation Status
              </label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as CaseStatus })}
                className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="Active">Active</option>
                <option value="Under Review">Under Review</option>
                <option value="Archived">Archived</option>
                <option value="Closed">Closed</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Tags (Comma separated)
            </label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              placeholder="Harassment, Financial, High Priority"
              className="w-full bg-[#0F172A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2.5 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setIsCreateOpen(false);
                setEditCase(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm">
              {editCase ? 'Save Changes' : 'Create Case'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Confirm Delete Dialog */}
      <ConfirmDialog
        isOpen={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleConfirmDelete}
        title={`Delete Case [${deleteTarget?.id}]?`}
        message="This action will delete the case and all associated evidence records. This cannot be undone."
        confirmLabel="Confirm Delete"
      />
    </div>
  );
};
