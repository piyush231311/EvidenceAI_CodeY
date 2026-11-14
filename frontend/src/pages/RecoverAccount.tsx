import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Eye, EyeOff, AlertCircle, KeyRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';
import { RecoveryCodesModal } from '../components/auth/RecoveryCodesModal';

export const RecoverAccount: React.FC = () => {
  const navigate = useNavigate();
  const { recover } = useAuth();

  const [username, setUsername] = useState<string>('');
  const [recoveryCode, setRecoveryCode] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // New recovery codes received after successful recovery
  const [newRecoveryCodes, setNewRecoveryCodes] = useState<string[] | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedUsername = username.trim();
    const cleanCode = recoveryCode.trim();

    if (!trimmedUsername || !cleanCode) {
      setError('Please provide both your username and one recovery code.');
      return;
    }

    if (newPassword.length < 12) {
      setError('New password must be at least 12 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match. Please verify both fields.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await recover(trimmedUsername, cleanCode, newPassword);
      if (res.recovery_codes && res.recovery_codes.length > 0) {
        setNewRecoveryCodes(res.recovery_codes);
      } else {
        navigate('/cases', { replace: true });
      }
    } catch (err: any) {
      setError(err.message || 'Recovery code or username was incorrect. Please verify and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCompleteNewCodes = () => {
    setNewRecoveryCodes(null);
    navigate('/cases', { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#FBFBF9] text-[#1C1917] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Modal presenting fresh batch of 8 recovery codes */}
      {newRecoveryCodes && (
        <RecoveryCodesModal
          codes={newRecoveryCodes}
          onComplete={handleCompleteNewCodes}
          title="Save your new recovery codes"
        />
      )}

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center px-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-white border border-[#E6E4DF] shadow-xs mb-3">
          <KeyRound className="w-6 h-6 text-[#0F766E]" />
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-[#1C1917]">
          Recover your account
        </h1>
        <p className="text-xs text-[#6B6862] mt-1.5 leading-relaxed">
          Use one of your 8-digit recovery codes to reset your password and regain access.
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-white border border-[#E6E4DF] py-7 px-6 sm:px-8 rounded-lg shadow-xs space-y-5">
          {error && (
            <div className="p-3 bg-[#FEF2F2] border border-[#FEE2E2] rounded text-xs text-[#991B1B] flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-[#DC2626] shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                Username or alias
              </label>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Your username"
                className="w-full h-9 px-3 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E]"
                disabled={submitting}
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                One recovery code
              </label>
              <input
                type="text"
                value={recoveryCode}
                onChange={(e) => setRecoveryCode(e.target.value.toUpperCase())}
                placeholder="e.g. 7K3F-9QX2-M8TD"
                className="w-full h-9 px-3 rounded text-xs font-mono uppercase bg-white border border-[#DCDAD4] text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E]"
                disabled={submitting}
              />
              <p className="text-[11px] text-[#6B6862] mt-1">
                Dashes and spaces are optional. You can paste the code directly.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                New passphrase
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 12 characters"
                  className="w-full h-9 pl-3 pr-10 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E]"
                  disabled={submitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#9C9890] hover:text-[#57534E] p-1"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                Confirm new passphrase
              </label>
              <input
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat new passphrase"
                className="w-full h-9 px-3 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E]"
                disabled={submitting}
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={submitting}
              className="w-full justify-center mt-2"
            >
              {submitting ? 'Resetting password...' : 'Reset password & regain access'}
            </Button>
          </form>

          <div className="pt-3 border-t border-[#F0EFEB] text-center text-xs">
            <span className="text-[#6B6862]">Remember your password? </span>
            <Link to="/login" className="font-medium text-[#0F766E] hover:underline">
              Return to sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
