import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Folder, 
  Upload, 
  Files, 
  Settings as SettingsIcon,
  Shield
} from 'lucide-react';
import { clsx } from 'clsx';
import { useApp } from '../../context/AppContext';

export const Sidebar: React.FC = () => {
  const { cases, evidence } = useApp();

  const navItems = [
    { name: 'Cases', path: '/cases', icon: Folder, count: cases.length },
    { name: 'Add evidence', path: '/upload', icon: Upload },
    { name: 'Evidence', path: '/evidence', icon: Files, count: evidence.length },
    { name: 'Settings', path: '/settings', icon: SettingsIcon },
  ];

  return (
    <aside className="w-56 bg-[#F4F3EE] border-r border-[#E6E4DF] flex flex-col justify-between shrink-0 select-none min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="h-14 flex items-center px-4 border-b border-[#E6E4DF]">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#0F766E]" />
            <span className="font-semibold text-sm text-[#1C1917] tracking-tight">Evidence AI</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-2 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center justify-between px-3 py-2 rounded text-xs font-medium transition-colors',
                    isActive
                      ? 'bg-white text-[#1C1917] border border-[#E6E4DF] font-semibold'
                      : 'text-[#6B6862] hover:text-[#1C1917] hover:bg-[#EAE8E1]'
                  )
                }
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4 text-[#6B6862]" />
                  <span>{item.name}</span>
                </div>
                {item.count !== undefined && item.count > 0 && (
                  <span className="text-[11px] font-mono text-[#6B6862]">
                    {item.count}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Reassurance Note */}
      <div className="p-3 border-t border-[#E6E4DF] text-[11px] text-[#6B6862] leading-tight">
        Local storage only. Files are not sent to any external server.
      </div>
    </aside>
  );
};
