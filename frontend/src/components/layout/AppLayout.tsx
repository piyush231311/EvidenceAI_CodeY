import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { useQuickExit } from '../../hooks/useQuickExit';
import { useInactivityTimeout } from '../../hooks/useInactivityTimeout';
import { SafetyModal } from '../common/SafetyModal';
import { Button } from '../common/Button';
import { ShieldAlert } from 'lucide-react';

export const AppLayout: React.FC = () => {
  // Global listener for double-Escape quick exit
  useQuickExit();

  // Inactivity auto-logout hook
  const { showWarning, countdown, staySignedIn, signOutNow } = useInactivityTimeout();

  return (
    <div className="min-h-screen flex bg-[#FBFBF9] text-[#1C1917]">
      <SafetyModal />

      {/* Inactivity Warning Dialog */}
      {showWarning && (
        <div className="fixed inset-0 z-50 bg-[#1C1917]/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#E6E4DF] rounded-lg max-w-sm w-full p-5 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0">
                <ShieldAlert className="w-4 h-4 text-amber-700" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#1C1917]">Are you still there?</h3>
                <p className="text-xs text-[#57534E] mt-1 leading-relaxed">
                  For your safety, Evidence AI will sign out in <span className="font-semibold text-[#1C1917]">{countdown} seconds</span> due to inactivity.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-[#F0EFEB]">
              <Button
                variant="secondary"
                size="sm"
                onClick={signOutNow}
              >
                Sign out now
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={staySignedIn}
              >
                Stay signed in
              </Button>
            </div>
          </div>
        </div>
      )}

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
