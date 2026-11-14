import React, { useState } from 'react';
import { Shield, HardDrive, CheckCircle2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const Settings: React.FC = () => {
  const { cases, evidence, deleteCase } = useApp();
  const [isClearOpen, setIsClearOpen] = useState<boolean>(false);
  const [clearMessage, setClearMessage] = useState<string>('');

  const handleClearAll = async () => {
    // Delete all cases sequentially
    for (const c of cases) {
      await deleteCase(c.id);
    }
    setIsClearOpen(false);
    setClearMessage('All cases and evidence records have been cleared from local database.');
    setTimeout(() => setClearMessage(''), 4000);
  };

  return (
    <div className="space-y-6 max-w-xl">
      <div className="pb-3 border-b border-[#E6E4DF]">
        <h1 className="text-lg font-semibold text-[#1C1917]">Settings</h1>
        <p className="text-xs text-[#6B6862] mt-0.5">
          Local storage and system details.
        </p>
      </div>

      {clearMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-900 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{clearMessage}</span>
        </div>
      )}

      {/* Storage and Privacy info */}
      <div className="bg-white border border-[#E6E4DF] rounded-md p-5 space-y-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
          Data storage & privacy
        </h3>

        <div className="space-y-3 text-xs">
          <div className="flex justify-between py-1.5 border-b border-[#F0EFEB]">
            <span className="text-[#6B6862]">Storage mode</span>
            <span className="font-medium text-[#1C1917]">Local only (SQLite database)</span>
          </div>

          <div className="flex justify-between py-1.5 border-b border-[#F0EFEB]">
            <span className="text-[#6B6862]">File storage path</span>
            <code className="text-[#1C1917] bg-[#F5F5F0] px-1 py-0.5 rounded font-mono text-[11px]">
              ./storage/originals/
            </code>
          </div>

          <div className="flex justify-between py-1.5 border-b border-[#F0EFEB]">
            <span className="text-[#6B6862]">Database file</span>
            <code className="text-[#1C1917] bg-[#F5F5F0] px-1 py-0.5 rounded font-mono text-[11px]">
              evidence_ai.db
            </code>
          </div>

          <div className="flex justify-between py-1.5">
            <span className="text-[#6B6862]">Database records</span>
            <span className="font-mono text-[#1C1917]">
              {cases.length} case{cases.length === 1 ? '' : 's'} • {evidence.length} file{evidence.length === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        <p className="text-xs text-[#6B6862] leading-relaxed pt-2">
          Your files and forensic records never leave this machine. SHA-256 cryptographic fingerprints are computed directly from raw bytes.
        </p>
      </div>

      {/* Clear Database */}
      <div className="bg-white border border-[#E6E4DF] rounded-md p-5 flex items-center justify-between gap-4">
        <div>
          <h4 className="text-xs font-semibold text-[#1C1917]">Clear all local cases</h4>
          <p className="text-xs text-[#6B6862] mt-0.5">
            Permanently delete all cases and evidence records from the local database.
          </p>
        </div>

        <Button
          variant="danger"
          size="sm"
          onClick={() => setIsClearOpen(true)}
          disabled={cases.length === 0}
        >
          Clear database
        </Button>
      </div>

      {/* App Version */}
      <div className="text-[11px] text-[#9C9890]">
        Evidence AI • Version 1.0.0
      </div>

      {/* Confirm Clear Dialog */}
      <ConfirmDialog
        isOpen={isClearOpen}
        onClose={() => setIsClearOpen(false)}
        onConfirm={handleClearAll}
        title="Clear all local data?"
        message="This will delete every case and all stored evidence files from the local database. This cannot be undone."
        confirmLabel="Clear all data"
      />
    </div>
  );
};
