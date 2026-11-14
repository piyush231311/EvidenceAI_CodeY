import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, LogOut, User as UserIcon, Power } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../common/Button';
import { triggerQuickExit } from '../../hooks/useQuickExit';

export const TopNavbar: React.FC = () => {
  const navigate = useNavigate();
  const { cases, activeCaseId, setActiveCaseId } = useApp();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <header className="h-14 bg-white border-b border-[#E6E4DF] px-6 flex items-center justify-between gap-4 sticky top-0 z-20 print:hidden">
      <div className="flex items-center gap-3">
        <span className="text-xs text-[#6B6862]">Active case:</span>
        {cases.length > 0 ? (
          <select
            value={activeCaseId}
            onChange={(e) => setActiveCaseId(e.target.value)}
            className="bg-[#FBFBF9] border border-[#E6E4DF] rounded px-2.5 py-1 text-xs text-[#1C1917] font-mono focus:outline-none focus:border-[#0F766E] cursor-pointer max-w-[220px] truncate"
            aria-label="Select active case"
          >
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id.substring(0, 16)}...
              </option>
            ))}
          </select>
        ) : (
          <span className="text-xs text-[#9C9890]">No cases created yet</span>
        )}
      </div>

      <div className="flex items-center gap-2.5">
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/upload')}
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Add evidence</span>
        </Button>

        {/* Authenticated User Badge */}
        {user && (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-[#FBFBF9] border border-[#E6E4DF] rounded-md text-xs text-[#1C1917] font-medium">
            <UserIcon className="w-3.5 h-3.5 text-[#0F766E]" />
            <span className="max-w-[150px] truncate" title={user.email}>
              {user.email}
            </span>
          </div>
        )}

        {/* Sign Out Button */}
        <button
          onClick={handleLogout}
          type="button"
          aria-label="Sign out of Evidence AI"
          title="Sign out of your session"
          className="h-8 px-2.5 rounded text-xs font-medium bg-white hover:bg-[#F9F9F8] text-[#57534E] hover:text-[#1C1917] border border-[#E6E4DF] transition-colors flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-[#0F766E]"
        >
          <Power className="w-3.5 h-3.5 text-[#78716C]" />
          <span className="hidden md:inline">Sign out</span>
        </button>

        {/* Quick Exit Button */}
        <button
          onClick={triggerQuickExit}
          type="button"
          aria-label="Quick exit to neutral site (Press Escape twice)"
          title="Instantly leave this page (or press Esc twice)"
          className="h-8 px-3 rounded text-xs font-medium bg-[#F0EFEB] hover:bg-[#E4E2DC] text-[#1C1917] border border-[#DCDAD4] transition-colors flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-[#0F766E]"
        >
          <LogOut className="w-3.5 h-3.5 text-[#57534E]" />
          <span>Quick exit</span>
        </button>
      </div>
    </header>
  );
};
