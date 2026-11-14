import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, ArrowRight, Folder, AlertCircle } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const Cases: React.FC = () => {
  const navigate = useNavigate();
  const { cases, createCase, deleteCase, isLoading, error, refreshData } = useApp();

  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [caseIdInput, setCaseIdInput] = useState<string>('');
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const created = await createCase(caseIdInput.trim() || undefined);
      setCaseIdInput('');
      setIsCreateOpen(false);
      navigate(`/cases/${created.id}`);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (deleteTargetId) {
      await deleteCase(deleteTargetId);
      setDeleteTargetId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Action */}
      <div className="flex items-center justify-between pb-3 border-b border-[#E6E4DF]">
        <div>
          <h1 className="text-lg font-semibold text-[#1C1917]">Cases</h1>
          <p className="text-xs text-[#6B6862] mt-0.5">Your cases and the evidence in them.</p>
        </div>

        <Button variant="primary" size="sm" onClick={() => setIsCreateOpen(true)}>
          <Plus className="w-3.5 h-3.5" />
          <span>New case</span>
        </Button>
      </div>

      {/* Cases Content */}
      {error ? (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-md p-8 text-center max-w-md mx-auto my-8">
          <AlertCircle className="w-8 h-8 text-rose-600 mx-auto mb-2" />
          <h3 className="text-sm font-semibold mb-1">Failed to load cases</h3>
          <p className="text-xs text-rose-700 mb-4">{error}</p>
          <Button variant="secondary" size="sm" onClick={() => refreshData()}>
            Retry connection
          </Button>
        </div>
      ) : isLoading ? (
        <div className="py-12 text-center text-xs text-[#6B6862]">Loading cases...</div>
      ) : cases.length === 0 ? (
        /* Empty State */
        <div className="bg-white border border-[#E6E4DF] rounded-md p-10 text-center max-w-md mx-auto my-8">
          <Folder className="w-8 h-8 text-[#9C9890] mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-[#1C1917] mb-1">No cases yet</h3>
          <p className="text-xs text-[#6B6862] mb-4">
            Create your first case to organize and store related evidence files together.
          </p>
          <Button variant="primary" size="sm" onClick={() => setIsCreateOpen(true)}>
            Create your first case
          </Button>
        </div>
      ) : (
        /* Case List as a clean Table */
        <div className="bg-white border border-[#E6E4DF] rounded-md overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#E6E4DF] bg-[#F9F9F7] text-[#6B6862]">
                <th className="py-2.5 px-4 font-medium">Case ID</th>
                <th className="py-2.5 px-4 font-medium">Files</th>
                <th className="py-2.5 px-4 font-medium">Created</th>
                <th className="py-2.5 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E6E4DF]">
              {cases.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/cases/${c.id}`)}
                  className="hover:bg-[#F9F9F7] cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-medium text-[#1C1917]">
                    {c.id}
                  </td>
                  <td className="py-3 px-4 text-[#6B6862]">
                    {c.evidence_count || 0} file{(c.evidence_count || 0) === 1 ? '' : 's'}
                  </td>
                  <td className="py-3 px-4 text-[#6B6862]">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="inline-flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => navigate(`/cases/${c.id}`)}
                        className="text-xs text-[#0F766E] hover:underline font-medium inline-flex items-center gap-1"
                      >
                        Open <ArrowRight className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => setDeleteTargetId(c.id)}
                        className="p-1 text-[#9C9890] hover:text-rose-600 rounded hover:bg-stone-100"
                        title="Delete case"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Case Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create new case"
        description="Cases group related files under one incident identifier."
        maxWidth="sm"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#1C1917] mb-1">
              Case ID (optional)
            </label>
            <input
              type="text"
              value={caseIdInput}
              onChange={(e) => setCaseIdInput(e.target.value)}
              placeholder="Leave empty to auto-generate a UUID"
              className="w-full bg-[#FBFBF9] border border-[#E6E4DF] rounded px-3 py-1.5 text-xs text-[#1C1917] font-mono placeholder:font-sans focus:outline-none focus:border-[#0F766E]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#F0EFEB]">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              Create case
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deleteTargetId !== null}
        onClose={() => setDeleteTargetId(null)}
        onConfirm={handleConfirmDelete}
        title="Delete case?"
        message="This will delete this case and remove all evidence files associated with it."
      />
    </div>
  );
};
