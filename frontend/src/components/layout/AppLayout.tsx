import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { useApp } from '../../context/AppContext';
import { clsx } from 'clsx';

export const AppLayout: React.FC = () => {
  const { settings } = useApp();

  return (
    <div className={clsx('min-h-screen flex bg-[#0B1120]', settings.theme === 'light' && 'theme-light')}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNavbar />
        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
