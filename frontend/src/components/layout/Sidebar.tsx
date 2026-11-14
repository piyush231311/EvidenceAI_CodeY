import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Briefcase, 
  UploadCloud, 
  FolderLock, 
  History, 
  Settings as SettingsIcon,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  HardDrive
} from 'lucide-react';
import { clsx } from 'clsx';
import { useApp } from '../../context/AppContext';

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const { cases, evidence } = useApp();

  const navItems = [
    { name: 'Overview', path: '/', icon: LayoutDashboard },
    { name: 'My Cases', path: '/cases', icon: Briefcase, badge: cases.length },
    { name: 'Upload Evidence', path: '/upload', icon: UploadCloud },
    { name: 'Evidence Vault', path: '/vault', icon: FolderLock, badge: evidence.length },
    { name: 'Recent Activity', path: '/activity', icon: History },
    { name: 'Settings', path: '/settings', icon: SettingsIcon },
  ];

  return (
    <aside
      className={clsx(
        'relative bg-[#0F172A] border-r border-slate-800 flex flex-col justify-between transition-all duration-300 z-30 select-none',
        collapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Brand Header */}
      <div>
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-white text-base tracking-tight leading-none">Evidence AI</span>
                <span className="text-[10px] text-cyan-400 font-mono tracking-wider uppercase mt-1">Intake & Vault</span>
              </div>
            )}
          </div>

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group relative',
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                  )
                }
                title={collapsed ? item.name : undefined}
              >
                <Icon className="w-5 h-5 shrink-0 transition-transform group-hover:scale-105" />
                {!collapsed && (
                  <span className="truncate flex-1">{item.name}</span>
                )}
                {!collapsed && item.badge !== undefined && (
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    {item.badge}
                  </span>
                )}
                {collapsed && item.badge !== undefined && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-blue-500" />
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Info Box */}
      <div className="p-3 border-t border-slate-800/80">
        {!collapsed ? (
          <div className="bg-[#162032] border border-slate-700/60 rounded-xl p-3">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-300 mb-1.5">
              <HardDrive className="w-3.5 h-3.5 text-cyan-400" />
              <span>Local Prototype Storage</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mb-2">
              <div className="bg-gradient-to-r from-blue-500 to-cyan-400 h-full w-[24%]" />
            </div>
            <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
              <span>{evidence.length} files saved</span>
              <span>Local Session</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center p-2 text-slate-500" title="Local Storage">
            <HardDrive className="w-5 h-5 text-cyan-400" />
          </div>
        )}
      </div>
    </aside>
  );
};
