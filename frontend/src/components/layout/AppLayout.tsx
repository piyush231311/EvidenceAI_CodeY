import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { useQuickExit } from '../../hooks/useQuickExit';
import { SafetyModal } from '../common/SafetyModal';

export const AppLayout: React.FC = () => {
  // Global listener for double-Escape quick exit
  useQuickExit();

  return (
    <div className="min-h-screen flex bg-[#FBFBF9] text-[#1C1917]">
      <SafetyModal />
      <div className="print:hidden">
        <Sidebar />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        <TopNavbar />
        <main className="flex-1 p-6 max-w-5xl w-full mx-auto print:p-0 print:max-w-none">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
