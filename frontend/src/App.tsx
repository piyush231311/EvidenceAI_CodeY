import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AppLayout } from './components/layout/AppLayout';
import { ErrorBoundary } from './components/common/ErrorBoundary';

import { Cases } from './pages/Cases';
import { CaseDetails } from './pages/CaseDetails';
import { UploadEvidence } from './pages/UploadEvidence';
import { EvidenceVault } from './pages/EvidenceVault';
import { Settings } from './pages/Settings';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
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
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/cases" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
