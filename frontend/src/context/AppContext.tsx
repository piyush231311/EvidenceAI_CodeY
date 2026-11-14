import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { Case, EvidenceFile } from '../types';
import { api } from '../services/api';
import { useAuth } from './AuthContext';

interface AppContextType {
  cases: Case[];
  evidence: EvidenceFile[];
  activeCaseId: string;
  isLoading: boolean;
  error: string | null;
  setActiveCaseId: (id: string) => void;
  createCase: (caseId?: string) => Promise<Case>;
  deleteCase: (caseId: string) => Promise<void>;
  uploadEvidence: (caseId: string, files: File[], notesMap?: Record<string, string>) => Promise<EvidenceFile[]>;
  deleteEvidence: (evidenceId: string) => Promise<void>;
  refreshData: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [evidence, setEvidence] = useState<EvidenceFile[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    if (!user) {
      setCases([]);
      setEvidence([]);
      setActiveCaseId('');
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const [fetchedCases, fetchedEvidence] = await Promise.all([
        api.getCases(),
        api.getAllEvidence()
      ]);

      // Calculate real evidence count per case from database records
      const countsMap: Record<string, number> = {};
      fetchedEvidence.forEach((item) => {
        countsMap[item.case_id] = (countsMap[item.case_id] || 0) + 1;
      });

      const enrichedCases = fetchedCases.map((c) => ({
        ...c,
        evidence_count: countsMap[c.id] || 0
      }));

      setCases(enrichedCases);
      setEvidence(fetchedEvidence);

      // Maintain activeCaseId or default to first case
      if (enrichedCases.length > 0 && (!activeCaseId || !enrichedCases.some((c) => c.id === activeCaseId))) {
        setActiveCaseId(enrichedCases[0].id);
      } else if (enrichedCases.length === 0) {
        setActiveCaseId('');
      }
    } catch (err: any) {
      console.error('Failed to load data from database:', err);
      setError('Unable to connect to local database server.');
    } finally {
      setIsLoading(false);
    }
  }, [user, activeCaseId]);

  useEffect(() => {
    if (user) {
      refreshData();
    } else {
      setCases([]);
      setEvidence([]);
      setActiveCaseId('');
      setIsLoading(false);
    }
  }, [user]);

  const createCase = async (caseId?: string) => {
    const created = await api.createCase(caseId);
    await refreshData();
    setActiveCaseId(created.id);
    return created;
  };

  const deleteCase = async (caseId: string) => {
    await api.deleteCase(caseId);
    await refreshData();
  };

  const uploadEvidence = async (caseId: string, files: File[], notesMap?: Record<string, string>) => {
    const uploaded = await api.uploadEvidence(caseId, files, notesMap);
    await refreshData();
    return uploaded;
  };

  const deleteEvidence = async (evidenceId: string) => {
    await api.deleteEvidence(evidenceId);
    await refreshData();
  };

  return (
    <AppContext.Provider
      value={{
        cases,
        evidence,
        activeCaseId,
        isLoading,
        error,
        setActiveCaseId,
        createCase,
        deleteCase,
        uploadEvidence,
        deleteEvidence,
        refreshData
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
