import React, { useState } from 'react';
import { 
  Settings as SettingsIcon, 
  Moon, 
  Sun, 
  RotateCcw, 
  Info, 
  Layers, 
  CheckCircle2, 
  Zap,
  Sparkles
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/common/Button';
import { ConfirmDialog } from '../components/common/ConfirmDialog';

export const Settings: React.FC = () => {
  const { settings, updateSettings, resetDemoWorkspace } = useApp();
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState<boolean>(false);
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string>('');

  const handleReset = () => {
    resetDemoWorkspace();
    setIsResetConfirmOpen(false);
    setResetSuccessMessage('Workspace reset to initial clean demo data.');
    setTimeout(() => setResetSuccessMessage(''), 3500);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-fadeIn">
      {/* Header */}
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <SettingsIcon className="w-6 h-6 text-slate-400" />
          Settings & Workspace Preferences
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Customize display density, theme, motion preferences, and manage demo prototype state.
        </p>
      </div>

      {resetSuccessMessage && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{resetSuccessMessage}</span>
        </div>
      )}

      {/* Preferences Section */}
      <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6 space-y-6">
        <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-3">
          Display & Interaction Preferences
        </h3>

        {/* Theme Preference */}
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-white block">Interface Color Theme</span>
            <span className="text-[11px] text-slate-400">
              Default is calibrated for high-contrast, low-eyestrain dark navy (#0B1120).
            </span>
          </div>

          <div className="flex items-center gap-2 bg-[#0F172A] border border-slate-700 rounded-xl p-1">
            <button
              onClick={() => updateSettings({ theme: 'dark' })}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                settings.theme === 'dark' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Moon className="w-3.5 h-3.5" /> Dark Navy
            </button>
            <button
              onClick={() => updateSettings({ theme: 'light' })}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                settings.theme === 'light' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sun className="w-3.5 h-3.5" /> Light
            </button>
          </div>
        </div>

        {/* Layout Density */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <div>
            <span className="text-xs font-semibold text-white block">Layout Density</span>
            <span className="text-[11px] text-slate-400">
              Controls padding and compactness across evidence cards and tables.
            </span>
          </div>

          <div className="flex items-center gap-2 bg-[#0F172A] border border-slate-700 rounded-xl p-1">
            <button
              onClick={() => updateSettings({ density: 'comfortable' })}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                settings.density === 'comfortable' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Comfortable
            </button>
            <button
              onClick={() => updateSettings({ density: 'compact' })}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                settings.density === 'compact' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Compact
            </button>
          </div>
        </div>

        {/* Reduced Motion Toggle */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <div>
            <span className="text-xs font-semibold text-white block">Reduced Motion</span>
            <span className="text-[11px] text-slate-400">
              Disable animated transitions for lower system utilization.
            </span>
          </div>

          <button
            onClick={() => updateSettings({ reducedMotion: !settings.reducedMotion })}
            className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${
              settings.reducedMotion ? 'bg-blue-600' : 'bg-slate-700'
            }`}
          >
            <div
              className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                settings.reducedMotion ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Demo Prototype Workspace Controls */}
      <div className="bg-[#162032] border border-slate-800 rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-3">
          Prototype Workspace Data Management
        </h3>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold text-white block">Reset Demonstration Workspace</span>
            <p className="text-[11px] text-slate-400 max-w-lg mt-0.5 leading-relaxed">
              Restore the initial 3 sample cases (Harassment, Financial Fraud, IP Theft) and 13 fictional evidence files. Newly created custom files will be cleared.
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsResetConfirmOpen(true)}
            className="shrink-0 text-slate-300 hover:text-white"
          >
            <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Reset Demo Workspace</span>
          </Button>
        </div>
      </div>

      {/* Application Version & Metadata */}
      <div className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 text-xs text-slate-400 space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-white">Evidence AI — Frontend Client</span>
          <span className="font-mono text-[11px] text-cyan-400">v2.0.0-hackathon</span>
        </div>
        <p className="text-[11px] leading-relaxed">
          Clean frontend-only build. Architecture is pre-wired with service abstractions (<code>caseService</code>, <code>evidenceService</code>) ready for FastAPI and local AI pipeline integrations.
        </p>
      </div>

      {/* Reset Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isResetConfirmOpen}
        onClose={() => setIsResetConfirmOpen(false)}
        onConfirm={handleReset}
        title="Reset Demo Workspace?"
        message="This will reset all cases, notes, and evidence to the original fictional demonstration dataset."
        confirmLabel="Reset Workspace"
        isDestructive={false}
      />
    </div>
  );
};
