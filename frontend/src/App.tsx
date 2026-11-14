import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppProvider } from './context/AppContext';
import { AppLayout } from './components/layout/AppLayout';
import { ErrorBoundary } from './components/common/ErrorBoundary';

import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { RecoverAccount } from './pages/RecoverAccount';
import { Cases } from './pages/Cases';
import { CaseDetails } from './pages/CaseDetails';
import { UploadEvidence } from './pages/UploadEvidence';
import { EvidenceVault } from './pages/EvidenceVault';
import { Guide } from './pages/Guide';
import { Settings } from './pages/Settings';

// Protected Route: redirects unauthenticated users to /login preserving target
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FBFBF9] flex items-center justify-center">
        <div className="text-xs text-[#6B6862] font-medium animate-pulse">
          Loading your workspace...
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

// Public Only Route: redirects authenticated users to /cases
const PublicOnlyRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return null;
  }

  if (user) {
    return <Navigate to="/cases" replace />;
  }

  return <>{children}</>;
};

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppProvider>
          <Routes>
            {/* Public standalone auth routes */}
            <Route
              path="/login"
              element={
                <PublicOnlyRoute>
                  <Login />
                </PublicOnlyRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicOnlyRoute>
                  <Register />
                </PublicOnlyRoute>
              }
            />
            <Route
              path="/recover"
              element={
                <PublicOnlyRoute>
                  <RecoverAccount />
                </PublicOnlyRoute>
              }
            />

            {/* App Layout routes */}
            <Route element={<AppLayout />}>
              {/* Public: Guide is always accessible without an account */}
              <Route path="/guide" element={<Guide />} />

              {/* Protected routes: require user session */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Navigate to="/cases" replace />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/cases"
                element={
                  <ProtectedRoute>
                    <Cases />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/cases/:id"
                element={
                  <ProtectedRoute>
                    <ErrorBoundary fallbackTitle="Case Details View Error">
                      <CaseDetails />
                    </ErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/upload"
                element={
                  <ProtectedRoute>
                    <UploadEvidence />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/evidence"
                element={
                  <ProtectedRoute>
                    <EvidenceVault />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <Settings />
                  </ProtectedRoute>
                }
              />

              {/* Catch-all */}
              <Route path="*" element={<Navigate to="/cases" replace />} />
            </Route>
          </Routes>
        </AppProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
