import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Eye, EyeOff, AlertCircle, Info } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';
import { RecoveryCodesModal } from '../components/auth/RecoveryCodesModal';

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const { register, user } = useAuth();

  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Recovery codes received after registration
  const [generatedCodes, setGeneratedCodes] = useState<string[] | null>(null);

  useEffect(() => {
    // Only redirect if already logged in and NOT currently viewing generated recovery codes
    if (user && !generatedCodes) {
      navigate('/cases', { replace: true });
    }
  }, [user, generatedCodes, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      setError('Please choose a username or alias.');
      return;
    }

    if (password.length < 12) {
      setError('Password must be at least 12 characters long. Try using four memorable words.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify both fields.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await register(trimmedUsername, password);
      if (res.recovery_codes && res.recovery_codes.length > 0) {
        setGeneratedCodes(res.recovery_codes);
      } else {
        navigate('/cases');
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your information.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCompleteRecoveryCodes = () => {
    setGeneratedCodes(null);
    navigate('/cases', { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#FBFBF9] text-[#1C1917] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Recovery Codes Modal shown after successful registration */}
      {generatedCodes && (
        <RecoveryCodesModal
          codes={generatedCodes}
          onComplete={handleCompleteRecoveryCodes}
          title="Save your 8 recovery codes"
        />
      )}

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center px-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-white border border-[#E6E4DF] shadow-xs mb-3">
          <Shield className="w-6 h-6 text-[#0F766E]" />
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-[#1C1917]">
          Create your private account
        </h1>
        <p className="text-xs text-[#6B6862] mt-1.5 leading-relaxed">
          You don't need an email address. We don't track who you are.
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
                placeholder="e.g. bluebird or reader42"
                className="w-full h-9 px-3 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E]"
                disabled={submitting}
                autoFocus
              />
              <p className="text-[11px] text-[#6B6862] mt-1">
                A nickname or alias is fine. Does not have to be your real name.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                Passphrase
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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
              <p className="text-[11px] text-[#6B6862] mt-1">
                At least 12 characters. Use a memorable phrase, like four random words.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                Confirm passphrase
              </label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat passphrase"
                  className="w-full h-9 pl-3 pr-10 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E]"
                  disabled={submitting}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  tabIndex={-1}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#9C9890] hover:text-[#57534E] p-1"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={submitting}
              className="w-full justify-center mt-2"
            >
              {submitting ? 'Creating account...' : 'Create account & get recovery codes'}
            </Button>
          </form>

          <div className="pt-3 border-t border-[#F0EFEB] text-center text-xs">
            <span className="text-[#6B6862]">Already have an account? </span>
            <Link to="/login" className="font-medium text-[#0F766E] hover:underline">
              Sign in
            </Link>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-[#6B6862]">
          <Link
            to="/guide"
            className="inline-flex items-center gap-1.5 text-[#0F766E] hover:underline font-medium"
          >
            <span>Need advice first? Read the safety and gathering guide</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
