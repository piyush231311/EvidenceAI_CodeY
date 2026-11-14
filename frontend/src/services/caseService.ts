import { Case, CaseNote } from '../types';
import { INITIAL_CASES } from '../data/mockData';

/**
 * CaseService Interface
 * Ready to be swapped with FastAPI endpoints (e.g. GET/POST /api/cases)
 */
export interface ICaseService {
  getCases(): Promise<Case[]>;
  getCaseById(id: string): Promise<Case | undefined>;
  createCase(caseData: Omit<Case, 'id' | 'createdAt' | 'updatedAt' | 'evidenceCount'>): Promise<Case>;
  updateCase(id: string, updates: Partial<Case>): Promise<Case>;
  deleteCase(id: string): Promise<boolean>;
  addNote(caseId: string, title: string, content: string): Promise<CaseNote>;
  updateNote(caseId: string, noteId: string, updates: Partial<CaseNote>): Promise<CaseNote>;
  deleteNote(caseId: string, noteId: string): Promise<boolean>;
}

class MockCaseService implements ICaseService {
  private cases: Case[] = [...INITIAL_CASES];

  async getCases(): Promise<Case[]> {
    return new Promise((resolve) => {
      setTimeout(() => resolve([...this.cases]), 100);
    });
  }

  async getCaseById(id: string): Promise<Case | undefined> {
    return new Promise((resolve) => {
      const found = this.cases.find((c) => c.id === id);
      setTimeout(() => resolve(found ? { ...found } : undefined), 50);
    });
  }

  async createCase(caseData: Omit<Case, 'id' | 'createdAt' | 'updatedAt' | 'evidenceCount'>): Promise<Case> {
    return new Promise((resolve) => {
      const now = new Date().toISOString();
      const randomSuffix = Math.floor(100 + Math.random() * 900);
      const newCase: Case = {
        ...caseData,
        id: `CASE-2026-${randomSuffix}`,
        createdAt: now,
        updatedAt: now,
        evidenceCount: 0,
        notes: []
      };
      this.cases.unshift(newCase);
      setTimeout(() => resolve(newCase), 100);
    });
  }

  async updateCase(id: string, updates: Partial<Case>): Promise<Case> {
    return new Promise((resolve, reject) => {
      const index = this.cases.findIndex((c) => c.id === id);
      if (index === -1) {
        reject(new Error(`Case with ID ${id} not found`));
        return;
      }
      this.cases[index] = {
        ...this.cases[index],
        ...updates,
        updatedAt: new Date().toISOString()
      };
      setTimeout(() => resolve(this.cases[index]), 100);
    });
  }

  async deleteCase(id: string): Promise<boolean> {
    return new Promise((resolve) => {
      this.cases = this.cases.filter((c) => c.id !== id);
      setTimeout(() => resolve(true), 100);
    });
  }

  async addNote(caseId: string, title: string, content: string): Promise<CaseNote> {
    return new Promise((resolve, reject) => {
      const targetCase = this.cases.find((c) => c.id === caseId);
      if (!targetCase) {
        reject(new Error(`Case ${caseId} not found`));
        return;
      }
      const now = new Date().toISOString();
      const note: CaseNote = {
        id: `note-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
        caseId,
        title,
        content,
        createdAt: now,
        updatedAt: now
      };
      targetCase.notes = [note, ...(targetCase.notes || [])];
      targetCase.updatedAt = now;
      setTimeout(() => resolve(note), 80);
    });
  }

  async updateNote(caseId: string, noteId: string, updates: Partial<CaseNote>): Promise<CaseNote> {
    return new Promise((resolve, reject) => {
      const targetCase = this.cases.find((c) => c.id === caseId);
      if (!targetCase || !targetCase.notes) {
        reject(new Error(`Case or notes not found`));
        return;
      }
      const noteIndex = targetCase.notes.findIndex((n) => n.id === noteId);
      if (noteIndex === -1) {
        reject(new Error(`Note ${noteId} not found`));
        return;
      }
      const updated = {
        ...targetCase.notes[noteIndex],
        ...updates,
        updatedAt: new Date().toISOString()
      };
      targetCase.notes[noteIndex] = updated;
      targetCase.updatedAt = new Date().toISOString();
      setTimeout(() => resolve(updated), 80);
    });
  }

  async deleteNote(caseId: string, noteId: string): Promise<boolean> {
    return new Promise((resolve, reject) => {
      const targetCase = this.cases.find((c) => c.id === caseId);
      if (!targetCase || !targetCase.notes) {
        reject(new Error(`Case or notes not found`));
        return;
      }
      targetCase.notes = targetCase.notes.filter((n) => n.id !== noteId);
      targetCase.updatedAt = new Date().toISOString();
      setTimeout(() => resolve(true), 80);
    });
  }
}

export const caseService = new MockCaseService();
