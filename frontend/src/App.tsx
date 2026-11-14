import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppProvider } from './context/AppContext';
import { AppLayout } from './components/layout/AppLayout';
import { ErrorBoundary } from './components/common/ErrorBoundary';

import { Login } from './pages/Login';
import { Cases } from './pages/Cases';
import { CaseDetails } from './pages/CaseDetails';
import { UploadEvidence } from './pages/UploadEvidence';
import { EvidenceVault } from './pages/EvidenceVault';
import { Guide } from './pages/Guide';
import { Settings } from './pages/Settings';

const AuthenticatedApp: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#FBFBF9] flex flex-col items-center justify-center font-sans">
        <div className="w-9 h-9 border-2 border-[#0F766E]/20 border-t-[#0F766E] rounded-full animate-spin mb-3" />
        <p className="text-xs text-[#6B6862] font-medium tracking-wide">
          Verifying Evidence AI session...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <AppProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/cases" replace />} />
          <Route path="/cases" element={<Cases />} />
          <Route
            path="/cases/:id"
            element={
              <ErrorBoundary fallbackTitle="Case Details View Error">
                <CaseDetails />
              </ErrorBoundary>
            }
          />
          <Route path="/upload" element={<UploadEvidence />} />
          <Route path="/evidence" element={<EvidenceVault />} />
          <Route path="/guide" element={<Guide />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/cases" replace />} />
        </Route>
      </Routes>
    </AppProvider>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AuthenticatedApp />
      </BrowserRouter>
    </AuthProvider>
  );
}
