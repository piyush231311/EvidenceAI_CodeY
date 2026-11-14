import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Shield, Eye, EyeOff, AlertCircle, Info, Lock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, user } = useAuth();

  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Check for inactivity logout notice in query params
  const searchParams = new URLSearchParams(location.search);
  const isInactivity = searchParams.get('reason') === 'inactivity';

  // If already logged in, redirect to destination or /cases
  useEffect(() => {
    if (user) {
      const from = (location.state as any)?.from?.pathname || '/cases';
      navigate(from, { replace: true });
    }
  }, [user, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please enter both your username and password.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      await login(username.trim(), password);
      const from = (location.state as any)?.from?.pathname || '/cases';
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || "Username or password didn't match. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FBFBF9] text-[#1C1917] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center px-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-white border border-[#E6E4DF] shadow-xs mb-3">
          <Shield className="w-6 h-6 text-[#0F766E]" />
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-[#1C1917]">
          Sign in to Evidence AI
        </h1>
        <p className="text-xs text-[#6B6862] mt-1.5 leading-relaxed">
          Your files stay on this device. Sign in to access your cases.
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-white border border-[#E6E4DF] py-7 px-6 sm:px-8 rounded-lg shadow-xs space-y-5">
          {isInactivity && (
            <div className="p-3 bg-[#FBFBF9] border border-[#E6E4DF] rounded text-xs text-[#6B6862] flex items-center gap-2">
              <Info className="w-4 h-4 text-[#0F766E] shrink-0" />
              <span>You were signed out because you were away.</span>
            </div>
          )}

          {error && (
            <div className="p-3 bg-[#FEF2F2] border border-[#FEE2E2] rounded text-xs text-[#991B1B] flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-[#DC2626] shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                Username
              </label>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Your username or alias"
                className="w-full h-9 px-3 rounded text-xs bg-white border border-[#DCDAD4] text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E]"
                disabled={submitting}
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#1C1917] mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Your password"
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

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={submitting}
              className="w-full justify-center mt-2"
            >
              {submitting ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <div className="pt-3 border-t border-[#F0EFEB] flex flex-col gap-2 text-center text-xs">
            <div>
              <span className="text-[#6B6862]">Don't have an account? </span>
              <Link to="/register" className="font-medium text-[#0F766E] hover:underline">
                Create an account
              </Link>
            </div>

            <div>
              <Link to="/recover" className="text-[#6B6862] hover:text-[#1C1917] hover:underline">
                Forgot password? Use a recovery code
              </Link>
            </div>
          </div>
        </div>

        {/* Safety & Guide Link */}
        <div className="mt-6 text-center text-xs text-[#6B6862]">
          <Link
            to="/guide"
            className="inline-flex items-center gap-1.5 text-[#0F766E] hover:underline font-medium"
          >
            <span>Gathering evidence safely? Read the guide first</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
