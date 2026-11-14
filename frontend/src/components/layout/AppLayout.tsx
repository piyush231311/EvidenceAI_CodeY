import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';

export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex bg-[#FBFBF9] text-[#1C1917]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNavbar />
        <main className="flex-1 p-6 max-w-5xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
