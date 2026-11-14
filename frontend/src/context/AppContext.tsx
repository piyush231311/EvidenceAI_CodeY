import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Case, EvidenceFile, ActivityRecord, AppSettings, CaseNote, ActivityAction } from '../types';
import { caseService } from '../services/caseService';
import { evidenceService } from '../services/evidenceService';
import { activityService } from '../services/activityService';
import { INITIAL_CASES, INITIAL_EVIDENCE, INITIAL_ACTIVITIES } from '../data/mockData';

interface AppContextType {
  cases: Case[];
  evidence: EvidenceFile[];
  activities: ActivityRecord[];
  activeCaseId: string;
  activeCase: Case | undefined;
  settings: AppSettings;
  isLoading: boolean;
  setActiveCaseId: (id: string) => void;
  createCase: (data: Omit<Case, 'id' | 'createdAt' | 'updatedAt' | 'evidenceCount'>) => Promise<Case>;
  updateCase: (id: string, updates: Partial<Case>) => Promise<Case>;
  deleteCase: (id: string) => Promise<boolean>;
  addCaseNote: (caseId: string, title: string, content: string) => Promise<CaseNote>;
  updateCaseNote: (caseId: string, noteId: string, updates: Partial<CaseNote>) => Promise<CaseNote>;
  deleteCaseNote: (caseId: string, noteId: string) => Promise<boolean>;
  addEvidenceItem: (item: Omit<EvidenceFile, 'id' | 'dateAdded'>) => Promise<EvidenceFile>;
  updateEvidenceItem: (id: string, updates: Partial<EvidenceFile>) => Promise<EvidenceFile>;
  deleteEvidenceItem: (id: string) => Promise<boolean>;
  deleteMultipleEvidence: (ids: string[]) => Promise<boolean>;
  updateSettings: (updates: Partial<AppSettings>) => void;
  resetDemoWorkspace: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cases, setCases] = useState<Case[]>([...INITIAL_CASES]);
  const [evidence, setEvidence] = useState<EvidenceFile[]>([...INITIAL_EVIDENCE]);
  const [activities, setActivities] = useState<ActivityRecord[]>([...INITIAL_ACTIVITIES]);
  const [activeCaseId, setActiveCaseId] = useState<string>('CASE-2026-081');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [settings, setSettings] = useState<AppSettings>({
    theme: 'dark',
    reducedMotion: false,
    density: 'comfortable',
    activeCaseId: 'CASE-2026-081'
  });

  // Calculate evidence counts for cases dynamically
  useEffect(() => {
    setCases((prevCases) =>
      prevCases.map((c) => ({
        ...c,
        evidenceCount: evidence.filter((e) => e.caseId === c.id).length
      }))
    );
  }, [evidence]);

  const activeCase = cases.find((c) => c.id === activeCaseId);

  const createCase = async (data: Omit<Case, 'id' | 'createdAt' | 'updatedAt' | 'evidenceCount'>) => {
    const created = await caseService.createCase(data);
    setCases((prev) => [created, ...prev]);
    await activityService.logActivity({
      caseId: created.id,
      caseTitle: created.title,
      action: 'CASE_CREATED',
      description: `Created new case: "${created.title}" [${created.id}]`
    });
    setActivities(await activityService.getActivities());
    return created;
  };

  const updateCase = async (id: string, updates: Partial<Case>) => {
    const updated = await caseService.updateCase(id, updates);
    setCases((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated } : c)));
    await activityService.logActivity({
      caseId: id,
      caseTitle: updated.title,
      action: updates.status ? 'CASE_STATUS_CHANGED' : 'CASE_EDITED',
      description: updates.status 
        ? `Status updated to "${updates.status}" for case [${id}]` 
        : `Updated details for case [${id}]`
    });
    setActivities(await activityService.getActivities());
    return updated;
  };

  const deleteCase = async (id: string) => {
    const target = cases.find((c) => c.id === id);
    await caseService.deleteCase(id);
    setCases((prev) => prev.filter((c) => c.id !== id));
    // Also remove associated evidence
    setEvidence((prev) => prev.filter((e) => e.caseId !== id));
    if (activeCaseId === id) {
      const remaining = cases.filter((c) => c.id !== id);
      setActiveCaseId(remaining.length > 0 ? remaining[0].id : '');
    }
    await activityService.logActivity({
      caseId: id,
      caseTitle: target?.title || id,
      action: 'CASE_DELETED',
      description: `Deleted case [${id}] and removed associated evidence.`
    });
    setActivities(await activityService.getActivities());
    return true;
  };

  const addCaseNote = async (caseId: string, title: string, content: string) => {
    const note = await caseService.addNote(caseId, title, content);
    setCases((prev) =>
      prev.map((c) => (c.id === caseId ? { ...c, notes: [note, ...(c.notes || [])] } : c))
    );
    await activityService.logActivity({
      caseId,
      action: 'NOTE_ADDED',
      description: `Added note: "${title}"`
    });
    setActivities(await activityService.getActivities());
    return note;
  };

  const updateCaseNote = async (caseId: string, noteId: string, updates: Partial<CaseNote>) => {
    const updatedNote = await caseService.updateNote(caseId, noteId, updates);
    setCases((prev) =>
      prev.map((c) => {
        if (c.id !== caseId || !c.notes) return c;
        return {
          ...c,
          notes: c.notes.map((n) => (n.id === noteId ? updatedNote : n))
        };
      })
    );
    await activityService.logActivity({
      caseId,
      action: 'NOTE_UPDATED',
      description: `Updated note: "${updatedNote.title}"`
    });
    setActivities(await activityService.getActivities());
    return updatedNote;
  };

  const deleteCaseNote = async (caseId: string, noteId: string) => {
    await caseService.deleteNote(caseId, noteId);
    setCases((prev) =>
      prev.map((c) => {
        if (c.id !== caseId || !c.notes) return c;
        return {
          ...c,
          notes: c.notes.filter((n) => n.id !== noteId)
        };
      })
    );
    await activityService.logActivity({
      caseId,
      action: 'NOTE_DELETED',
      description: `Deleted note from case [${caseId}]`
    });
    setActivities(await activityService.getActivities());
    return true;
  };

  const addEvidenceItem = async (item: Omit<EvidenceFile, 'id' | 'dateAdded'>) => {
    const created = await evidenceService.addEvidence(item);
    setEvidence((prev) => [created, ...prev]);
    await activityService.logActivity({
      caseId: created.caseId,
      evidenceId: created.id,
      evidenceName: created.displayName,
      action: 'EVIDENCE_ADDED',
      description: `Uploaded evidence "${created.displayName}" (${created.fileName})`
    });
    setActivities(await activityService.getActivities());
    return created;
  };

  const updateEvidenceItem = async (id: string, updates: Partial<EvidenceFile>) => {
    const updated = await evidenceService.updateEvidence(id, updates);
    setEvidence((prev) => prev.map((e) => (e.id === id ? updated : e)));
    await activityService.logActivity({
      caseId: updated.caseId,
      evidenceId: updated.id,
      evidenceName: updated.displayName,
      action: 'EVIDENCE_EDITED',
      description: `Updated metadata for "${updated.displayName}"`
    });
    setActivities(await activityService.getActivities());
    return updated;
  };

  const deleteEvidenceItem = async (id: string) => {
    const target = evidence.find((e) => e.id === id);
    await evidenceService.deleteEvidence(id);
    setEvidence((prev) => prev.filter((e) => e.id !== id));
    await activityService.logActivity({
      caseId: target?.caseId || '',
      evidenceId: id,
      evidenceName: target?.displayName || id,
      action: 'EVIDENCE_REMOVED',
      description: `Removed evidence "${target?.displayName || id}"`
    });
    setActivities(await activityService.getActivities());
    return true;
  };

  const deleteMultipleEvidence = async (ids: string[]) => {
    await evidenceService.deleteMultiple(ids);
    setEvidence((prev) => prev.filter((e) => !ids.includes(e.id)));
    await activityService.logActivity({
      caseId: activeCaseId,
      action: 'EVIDENCE_REMOVED',
      description: `Bulk deleted ${ids.length} evidence items.`
    });
    setActivities(await activityService.getActivities());
    return true;
  };

  const updateSettings = (updates: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  const resetDemoWorkspace = () => {
    setCases([...INITIAL_CASES]);
    setEvidence([...INITIAL_EVIDENCE]);
    setActivities([...INITIAL_ACTIVITIES]);
    setActiveCaseId('CASE-2026-081');
  };

  return (
    <AppContext.Provider
      value={{
        cases,
        evidence,
        activities,
        activeCaseId,
        activeCase,
        settings,
        isLoading,
        setActiveCaseId,
        createCase,
        updateCase,
        deleteCase,
        addCaseNote,
        updateCaseNote,
        deleteCaseNote,
        addEvidenceItem,
        updateEvidenceItem,
        deleteEvidenceItem,
        deleteMultipleEvidence,
        updateSettings,
        resetDemoWorkspace
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
