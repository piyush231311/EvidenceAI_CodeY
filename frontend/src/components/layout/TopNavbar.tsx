import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  UploadCloud, 
  Bell, 
  Sun, 
  Moon, 
  Briefcase, 
  CheckCircle2, 
  ExternalLink,
  X
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Button } from '../common/Button';

export const TopNavbar: React.FC = () => {
  const navigate = useNavigate();
  const { cases, evidence, activeCaseId, setActiveCaseId, activities, settings, updateSettings } = useApp();

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);

  // Filter cases and evidence for search query
  const searchResults = searchQuery.trim() === '' ? [] : [
    ...cases
      .filter((c) => c.title.toLowerCase().includes(searchQuery.toLowerCase()) || c.id.toLowerCase().includes(searchQuery.toLowerCase()))
      .map((c) => ({ type: 'case', id: c.id, title: c.title, path: `/cases/${c.id}` })),
    ...evidence
      .filter((e) => e.displayName.toLowerCase().includes(searchQuery.toLowerCase()) || e.fileName.toLowerCase().includes(searchQuery.toLowerCase()) || e.id.toLowerCase().includes(searchQuery.toLowerCase()))
      .map((e) => ({ type: 'evidence', id: e.id, title: e.displayName, path: `/vault/${e.id}` }))
  ];

  const handleSelectSearchResult = (path: string) => {
    navigate(path);
    setSearchQuery('');
    setShowSearchResults(false);
  };

  const toggleTheme = () => {
    const nextTheme = settings.theme === 'dark' ? 'light' : 'dark';
    updateSettings({ theme: nextTheme });
  };

  return (
    <header className="h-16 bg-[#0B1120]/90 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between gap-4 sticky top-0 z-20">
      {/* Global Search Bar */}
      <div className="relative flex-1 max-w-md">
        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
          <input
            type="text"
            placeholder="Search cases, evidence files, or hashes..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowSearchResults(true);
            }}
            onFocus={() => setShowSearchResults(true)}
            className="w-full bg-[#162032] border border-slate-700/80 rounded-xl pl-9 pr-8 py-2 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery('');
                setShowSearchResults(false);
              }}
              className="absolute right-3 text-slate-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Search Results Dropdown */}
        {showSearchResults && searchQuery.trim() !== '' && (
          <div className="absolute left-0 right-0 top-12 bg-[#162032] border border-slate-700 rounded-xl shadow-2xl p-2 z-50 max-h-80 overflow-y-auto">
            {searchResults.length === 0 ? (
              <div className="p-3 text-xs text-slate-400 text-center">No cases or files match "{searchQuery}"</div>
            ) : (
              <div className="space-y-1">
                {searchResults.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleSelectSearchResult(item.path)}
                    className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-slate-800 text-left transition-colors group"
                  >
                    <div className="flex items-center gap-2.5 overflow-hidden">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 uppercase">
                        {item.type}
                      </span>
                      <span className="text-xs font-medium text-slate-200 group-hover:text-blue-400 truncate">
                        {item.title}
                      </span>
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400 shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Active Case Selector */}
        <div className="flex items-center gap-2 bg-[#162032] border border-slate-700/80 rounded-xl px-3 py-1.5">
          <Briefcase className="w-3.5 h-3.5 text-blue-400 shrink-0" />
          <select
            value={activeCaseId}
            onChange={(e) => setActiveCaseId(e.target.value)}
            className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer max-w-[180px] truncate"
          >
            {cases.map((c) => (
              <option key={c.id} value={c.id} className="bg-[#162032] text-slate-200">
                {c.id} — {c.title}
              </option>
            ))}
          </select>
        </div>

        {/* Quick Upload Button */}
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/upload')}
          className="shadow-md shadow-blue-500/20"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Upload Evidence</span>
        </Button>

        {/* Notifications Popover Toggle */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition-colors relative"
            title="Activity Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-400 ring-2 ring-[#0B1120]" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-12 w-80 bg-[#162032] border border-slate-700 rounded-xl shadow-2xl p-3 z-50">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
                <span className="text-xs font-semibold text-white">Recent Case Events</span>
                <span className="text-[10px] text-slate-400 font-mono">{activities.length} total</span>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {activities.slice(0, 5).map((act) => (
                  <div key={act.id} className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-xs">
                    <p className="text-slate-200 text-[11px] leading-snug">{act.description}</p>
                    <span className="text-[10px] text-slate-400 mt-1 block font-mono">
                      {new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => {
                  setShowNotifications(false);
                  navigate('/activity');
                }}
                className="w-full mt-2.5 text-center text-[11px] text-cyan-400 hover:underline py-1"
              >
                View full activity audit log →
              </button>
            </div>
          )}
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition-colors"
          title={`Switch to ${settings.theme === 'dark' ? 'Light' : 'Dark'} Mode`}
        >
          {settings.theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-300" />}
        </button>
      </div>
    </header>
  );
};
