import { EvidenceFile, EvidenceType } from '../types';
import { INITIAL_EVIDENCE } from '../data/mockData';

export interface IEvidenceService {
  getEvidence(caseId?: string, fileType?: EvidenceType): Promise<EvidenceFile[]>;
  getEvidenceById(id: string): Promise<EvidenceFile | undefined>;
  addEvidence(fileData: Omit<EvidenceFile, 'id' | 'dateAdded'>): Promise<EvidenceFile>;
  updateEvidence(id: string, updates: Partial<EvidenceFile>): Promise<EvidenceFile>;
  deleteEvidence(id: string): Promise<boolean>;
  deleteMultiple(ids: string[]): Promise<boolean>;
}

class MockEvidenceService implements IEvidenceService {
  private evidence: EvidenceFile[] = [...INITIAL_EVIDENCE];

  async getEvidence(caseId?: string, fileType?: EvidenceType): Promise<EvidenceFile[]> {
    return new Promise((resolve) => {
      let filtered = [...this.evidence];
      if (caseId) {
        filtered = filtered.filter((e) => e.caseId === caseId);
      }
      if (fileType) {
        filtered = filtered.filter((e) => e.fileType === fileType);
      }
      setTimeout(() => resolve(filtered), 100);
    });
  }

  async getEvidenceById(id: string): Promise<EvidenceFile | undefined> {
    return new Promise((resolve) => {
      const item = this.evidence.find((e) => e.id === id);
      setTimeout(() => resolve(item ? { ...item } : undefined), 50);
    });
  }

  async addEvidence(fileData: Omit<EvidenceFile, 'id' | 'dateAdded'>): Promise<EvidenceFile> {
    return new Promise((resolve) => {
      const typePrefix = fileData.fileType.substring(0, 3).toUpperCase();
      const randomSuffix = Math.floor(100 + Math.random() * 900);
      const newEvidence: EvidenceFile = {
        ...fileData,
        id: `EVD-${typePrefix}-${randomSuffix}`,
        dateAdded: new Date().toISOString()
      };
      this.evidence.unshift(newEvidence);
      setTimeout(() => resolve(newEvidence), 120);
    });
  }

  async updateEvidence(id: string, updates: Partial<EvidenceFile>): Promise<EvidenceFile> {
    return new Promise((resolve, reject) => {
      const index = this.evidence.findIndex((e) => e.id === id);
      if (index === -1) {
        reject(new Error(`Evidence with ID ${id} not found`));
        return;
      }
      this.evidence[index] = {
        ...this.evidence[index],
        ...updates
      };
      setTimeout(() => resolve(this.evidence[index]), 100);
    });
  }

  async deleteEvidence(id: string): Promise<boolean> {
    return new Promise((resolve) => {
      this.evidence = this.evidence.filter((e) => e.id !== id);
      setTimeout(() => resolve(true), 100);
    });
  }

  async deleteMultiple(ids: string[]): Promise<boolean> {
    return new Promise((resolve) => {
      const idSet = new Set(ids);
      this.evidence = this.evidence.filter((e) => !idSet.has(e.id));
      setTimeout(() => resolve(true), 120);
    });
  }
}

export const evidenceService = new MockEvidenceService();
