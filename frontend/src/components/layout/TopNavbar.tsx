import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Button } from '../common/Button';

export const TopNavbar: React.FC = () => {
  const navigate = useNavigate();
  const { cases, activeCaseId, setActiveCaseId } = useApp();

  return (
    <header className="h-14 bg-white border-b border-[#E6E4DF] px-6 flex items-center justify-between gap-4 sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <span className="text-xs text-[#6B6862]">Active case:</span>
        {cases.length > 0 ? (
          <select
            value={activeCaseId}
            onChange={(e) => setActiveCaseId(e.target.value)}
            className="bg-[#FBFBF9] border border-[#E6E4DF] rounded px-2.5 py-1 text-xs text-[#1C1917] font-mono focus:outline-none focus:border-[#0F766E] cursor-pointer max-w-[220px] truncate"
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

      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/upload')}
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Add evidence</span>
        </Button>
      </div>
    </header>
  );
};
