import React, { useState } from 'react';
import { Shield, Lock, Mail, ArrowRight, Sparkles, AlertCircle, Eye, EyeOff, KeyRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';

export const Login: React.FC = () => {
  const { login, error, clearError, demoCredentials } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const defaultDemoEmail = demoCredentials?.email || 'demo@evidenceai.local';
  const defaultDemoPassword = demoCredentials?.password || 'DemoUser123!';

  const handleAutofill = () => {
    setEmail(defaultDemoEmail);
    setPassword(defaultDemoPassword);
    clearError();
    setLocalError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setLocalError('Please enter both email and password.');
      return;
    }

    try {
      setLocalError(null);
      setIsSubmitting(true);
      await login(email.trim(), password);
    } catch (err: any) {
      setLocalError(err.message || 'Invalid email or password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen bg-[#FBFBF9] flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#0F766E] text-white shadow-sm mb-4">
          <Shield className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-[#1C1917]">
          Evidence AI
        </h1>
        <p className="mt-1 text-sm text-[#57534E]">
          Victim-First Digital Forensics & Investigation Intelligence
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 shadow-sm border border-[#E6E4DF] rounded-xl sm:px-10">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-[#1C1917]">Sign In</h2>
            <p className="text-xs text-[#6B6862] mt-0.5">
              Enter your credentials to access your cases and analysis.
            </p>
          </div>

          {displayError && (
            <div
              role="alert"
              className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 font-medium">{displayError}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email-input"
                className="block text-xs font-medium text-[#1C1917] mb-1"
              >
                Email Address
              </label>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#9C9890]">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="email-input"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (displayError) {
                      clearError();
                      setLocalError(null);
                    }
                  }}
                  placeholder="analyst@agency.local"
                  required
                  autoComplete="email"
                  className="block w-full pl-9 pr-3 py-2 border border-[#E6E4DF] rounded-lg text-sm bg-[#FDFDFC] text-[#1C1917] placeholder-[#A8A29E] focus:outline-none focus:ring-2 focus:ring-[#0F766E] focus:border-transparent transition-colors"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password-input"
                className="block text-xs font-medium text-[#1C1917] mb-1"
              >
                Password
              </label>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#9C9890]">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="password-input"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (displayError) {
                      clearError();
                      setLocalError(null);
                    }
                  }}
                  placeholder="••••••••••••"
                  required
                  autoComplete="current-password"
                  className="block w-full pl-9 pr-10 py-2 border border-[#E6E4DF] rounded-lg text-sm bg-[#FDFDFC] text-[#1C1917] placeholder-[#A8A29E] focus:outline-none focus:ring-2 focus:ring-[#0F766E] focus:border-transparent transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#9C9890] hover:text-[#57534E] focus:outline-none"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                size="md"
                className="w-full justify-center text-sm font-medium py-2.5 shadow-sm"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Signing in...</span>
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </span>
                )}
              </Button>
            </div>
          </form>

          {/* Development / Demo Account Box */}
          <div className="mt-6 pt-5 border-t border-[#E6E4DF]">
            <div className="bg-[#F8FAF9] border border-[#D5E5E2] rounded-lg p-3.5 text-xs text-[#292524]">
              <div className="flex items-center justify-between mb-2">
                <span className="inline-flex items-center gap-1 font-semibold text-[#0F766E] uppercase tracking-wider text-[10px]">
                  <KeyRound className="w-3.5 h-3.5" />
                  Demo Account Credentials
                </span>
                <span className="text-[10px] font-mono text-[#57534E] bg-white px-1.5 py-0.5 rounded border border-[#E6E4DF]">
                  Dev Environment
                </span>
              </div>

              <div className="space-y-1 font-mono text-xs text-[#334155] bg-white p-2.5 rounded border border-[#E6E4DF]">
                <div className="flex items-center justify-between">
                  <span className="text-[#64748B]">Email:</span>
                  <span className="font-semibold select-all text-[#0F766E]">
                    {defaultDemoEmail}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#64748B]">Password:</span>
                  <span className="font-semibold select-all text-[#0F766E]">
                    {defaultDemoPassword}
                  </span>
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between gap-2">
                <p className="text-[11px] text-[#64748B] leading-tight">
                  Public demo credentials for safe testing and walkthrough.
                </p>
                <button
                  type="button"
                  onClick={handleAutofill}
                  className="flex-shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-[#0F766E] bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-[#0F766E]"
                  title="Autofill the login form with demo credentials"
                >
                  <Sparkles className="w-3 h-3 text-[#0F766E]" />
                  <span>One-Click Autofill</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-[#78716C]">
          Forensic Integrity &bull; Append-Only Audit Logging &bull; Zero Mock Data
        </p>
      </div>
    </div>
  );
};
