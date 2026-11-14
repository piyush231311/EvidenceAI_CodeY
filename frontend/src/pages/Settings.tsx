import React, { useState } from 'react';
import { 
  Shield, 
  CheckCircle2, 
  RotateCcw, 
  AlertTriangle, 
  ExternalLink, 
  Info,
  User as UserIcon,
  KeyRound,
  Lock,
  LogOut,
  AlertCircle
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { RecoveryCodesModal } from '../components/auth/RecoveryCodesModal';
import { quickExitNotice, disclaimer } from '../content/guidance.js';

export const Settings: React.FC = () => {
  const { cases, evidence, deleteCase } = useApp();
  const { user, changePassword, regenerateRecoveryCodes, logout } = useAuth();
  
  const [isClearOpen, setIsClearOpen] = useState<boolean>(false);
  const [clearMessage, setClearMessage] = useState<string>('');

  // Change password state
  const [isChangingPassword, setIsChangingPassword] = useState<boolean>(false);
  const [currentPassword, setCurrentPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [passwordSuccess, setPasswordSuccess] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState<boolean>(false);

  // Regenerate recovery codes state
  const [isRegenerateOpen, setIsRegenerateOpen] = useState<boolean>(false);
  const [regenPassword, setRegenPassword] = useState<string>('');
  const [regenError, setRegenError] = useState<string>('');
  const [isRegenSubmitting, setIsRegenSubmitting] = useState<boolean>(false);
  const [newCodes, setNewCodes] = useState<string[] | null>(null);

  // Sign out all devices confirm
  const [isSignoutAllOpen, setIsSignoutAllOpen] = useState<boolean>(false);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (!currentPassword) {
      setPasswordError('Please enter your current password.');
      return;
    }

    if (newPassword.length < 12) {
      setPasswordError('New password must be at least 12 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    try {
      setIsPasswordSubmitting(true);
      await changePassword(currentPassword, newPassword);
      setPasswordSuccess('Password updated successfully. Other active sessions have been invalidated.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setIsChangingPassword(false);
      setTimeout(() => setPasswordSuccess(''), 5000);
    } catch (err: any) {
      setPasswordError(err.message || 'Failed to update password. Please check your current password.');
    } finally {
      setIsPasswordSubmitting(false);
    }
  };

  const handleRegenerateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegenError('');

    if (!regenPassword) {
      setRegenError('Please enter your password to confirm.');
      return;
    }

    try {
      setIsRegenSubmitting(true);
      const codes = await regenerateRecoveryCodes(regenPassword);
      setRegenPassword('');
      setIsRegenerateOpen(false);
      setNewCodes(codes);
    } catch (err: any) {
      setRegenError(err.message || 'Incorrect password.');
    } finally {
      setIsRegenSubmitting(false);
    }
  };

  const handleSignoutAll = async () => {
    setIsSignoutAllOpen(false);
    await logout(true);
  };

  const handleClearAll = async () => {
    // Delete all cases sequentially
    for (const c of cases) {
      await deleteCase(c.id);
    }
    setIsClearOpen(false);
    setClearMessage('All cases and evidence records have been cleared from local database.');
    setTimeout(() => setClearMessage(''), 4000);
  };

  const handleShowSafetyModal = () => {
    localStorage.removeItem('evidence_ai_safety_onboarding_completed');
    window.dispatchEvent(new CustomEvent('evidence-ai-open-safety-modal'));
  };

  return (
    <div className="space-y-6 max-w-xl pb-12">
      {/* Recovery codes display modal if regenerated */}
      {newCodes && (
        <RecoveryCodesModal
          codes={newCodes}
          onComplete={() => setNewCodes(null)}
          title="New recovery codes"
        />
      )}

      {/* Regenerate codes password prompt dialog */}
      {isRegenerateOpen && (
        <div className="fixed inset-0 z-50 bg-[#1C1917]/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#E6E4DF] rounded-lg max-w-sm w-full p-5 shadow-xl space-y-4">
            <h3 className="text-sm font-semibold text-[#1C1917]">Regenerate recovery codes</h3>
            <p className="text-xs text-[#57534E] leading-relaxed">
              Generating new recovery codes will immediately invalidate all previously issued codes. Enter your current password to proceed.
            </p>

            {regenError && (
              <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded text-xs text-[#991B1B]">
                {regenError}
              </div>
            )}

            <form onSubmit={handleRegenerateSubmit} className="space-y-3">
              <input
                type="password"
                value={regenPassword}
                onChange={(e) => setRegenPassword(e.target.value)}
                placeholder="Current password"
                className="w-full h-8 px-2.5 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] focus:outline-none focus:border-[#0F766E]"
                autoFocus
              />

              <div className="flex justify-end gap-2 pt-1">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setIsRegenerateOpen(false);
                    setRegenPassword('');
                    setRegenError('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isRegenSubmitting}
                >
                  {isRegenSubmitting ? 'Generating...' : 'Regenerate codes'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sign out all devices confirm dialog */}
      <ConfirmDialog
        isOpen={isSignoutAllOpen}
        onClose={() => setIsSignoutAllOpen(false)}
        onConfirm={handleSignoutAll}
        title="Sign out on all devices?"
        message="This will immediately invalidate all active sessions across all browsers and devices. You will need to sign in again."
        confirmLabel="Sign out everywhere"
      />

      <div className="pb-3 border-b border-[#E6E4DF]">
        <h1 className="text-lg font-semibold text-[#1C1917]">Settings</h1>
        <p className="text-xs text-[#6B6862] mt-0.5">
          Account security, safety preferences, and local storage.
        </p>
      </div>

      {clearMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-900 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{clearMessage}</span>
        </div>
      )}

      {passwordSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-900 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{passwordSuccess}</span>
        </div>
      )}

      {/* ACCOUNT & SECURITY SECTION */}
      {user && (
        <div className="bg-white border border-[#E6E4DF] rounded-md p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#F0EFEB]">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
                Account security
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <UserIcon className="w-3.5 h-3.5 text-[#0F766E]" />
                <span className="text-xs text-[#1C1917]">
                  Signed in as <strong className="font-semibold text-[#1C1917]">{user.username}</strong>
                </span>
              </div>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsChangingPassword(!isChangingPassword)}
            >
              <Lock className="w-3.5 h-3.5" />
              <span>{isChangingPassword ? 'Cancel password change' : 'Change password'}</span>
            </Button>
          </div>

          {/* Change Password Inline Form */}
          {isChangingPassword && (
            <div className="p-4 bg-[#FAF9F5] border border-[#E6E4DF] rounded-md space-y-3">
              <h3 className="text-xs font-semibold text-[#1C1917]">Update passphrase</h3>
              
              {passwordError && (
                <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded text-xs text-[#991B1B] flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-[#DC2626] shrink-0" />
                  <span>{passwordError}</span>
                </div>
              )}

              <form onSubmit={handlePasswordSubmit} className="space-y-3">
                <div>
                  <label className="block text-[11px] font-medium text-[#1C1917] mb-1">
                    Current password
                  </label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full h-8 px-2.5 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] focus:outline-none focus:border-[#0F766E]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-[#1C1917] mb-1">
                    New passphrase (at least 12 characters)
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full h-8 px-2.5 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] focus:outline-none focus:border-[#0F766E]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-[#1C1917] mb-1">
                    Confirm new passphrase
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full h-8 px-2.5 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] focus:outline-none focus:border-[#0F766E]"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={isPasswordSubmitting}
                  >
                    {isPasswordSubmitting ? 'Updating...' : 'Update password'}
                  </Button>
                </div>
              </form>
            </div>
          )}

          {/* Recovery Codes & Session Management */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
            <div>
              <h4 className="text-xs font-semibold text-[#1C1917]">Account recovery codes</h4>
              <p className="text-[11px] text-[#6B6862]">
                Generate a fresh set of 8 codes if you have used or misplaced existing ones.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsRegenerateOpen(true)}
              className="shrink-0"
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>Regenerate recovery codes</span>
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-3 border-t border-[#F0EFEB]">
            <div>
              <h4 className="text-xs font-semibold text-[#1C1917]">Global session sign out</h4>
              <p className="text-[11px] text-[#6B6862]">
                Invalidates all active login sessions on any shared or saved computers.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsSignoutAllOpen(true)}
              className="shrink-0 text-[#991B1B] hover:text-[#7F1D1D]"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign out on all devices</span>
            </Button>
          </div>
        </div>
      )}

      {/* Safety Onboarding Reminder */}
      <div className="bg-white border border-[#E6E4DF] rounded-md p-5 flex items-center justify-between gap-4">
        <div>
          <h3 className="text-xs font-semibold text-[#1C1917]">Safety guidance screen</h3>
          <p className="text-xs text-[#6B6862] mt-0.5">
            Re-read the 3-step safety reminders shown when Evidence AI was first opened.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={handleShowSafetyModal}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Show again</span>
        </Button>
      </div>

      {/* Quick exit & Browsing Privacy Notice */}
      <div className="bg-white border border-[#E6E4DF] rounded-md p-5 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
          Quick exit & browsing privacy
        </h3>

        <p className="text-xs text-[#44403C] leading-relaxed">
          {quickExitNotice.summary} You can also trigger it instantly from anywhere by pressing the <kbd className="font-mono bg-[#F5F5F0] border border-[#E6E4DF] px-1 py-0.5 rounded text-[11px] text-[#1C1917]">Escape</kbd> key twice quickly.
        </p>

        <div className="p-3 bg-[#FFFDF5] border border-[#F3E7C4] rounded text-xs text-[#785412] leading-relaxed">
          <span className="font-medium">{quickExitNotice.warning}</span>
        </div>

        <div className="space-y-1.5 pt-1">
          <h4 className="text-xs font-semibold text-[#1C1917]">To stay safe while browsing:</h4>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-[#57534E] leading-relaxed">
            {quickExitNotice.privacyTips.map((tip, idx) => (
              <li key={idx}>{tip}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Storage and Privacy info */}
      <div className="bg-white border border-[#E6E4DF] rounded-md p-5 space-y-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
          Data storage & security
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

      {/* Quiet Footer Note */}
      <div className="pt-2 text-[11px] text-[#9C9890] flex items-start gap-1.5 leading-relaxed">
        <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
        <span>{disclaimer.text}</span>
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
