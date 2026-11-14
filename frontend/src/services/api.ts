// Evidence AI - Direct Backend API Service (Zero Mock Data)

export interface ApiCase {
  id: string;
  created_at: string;
  evidence_count?: number;
}

export interface ApiEvidence {
  id: string;
  case_id: string;
  original_filename: string;
  stored_path: string;
  file_type: 'image' | 'audio' | 'text';
  mime_type: string;
  size_bytes: number;
  sha256: string;
  notes: string | null;
  authenticity_passed: boolean;
  authenticity_score: number | null;
  uploaded_at: string;
}

const API_BASE = '/api';

export const api = {
  // Cases
  async getCases(): Promise<ApiCase[]> {
    const res = await fetch(`${API_BASE}/cases`);
    if (!res.ok) throw new Error('Failed to load cases');
    return res.json();
  },

  async createCase(caseId?: string): Promise<ApiCase> {
    const res = await fetch(`${API_BASE}/cases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(caseId ? { id: caseId } : {})
    });
    if (!res.ok) throw new Error('Failed to create case');
    return res.json();
  },

  async deleteCase(caseId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/cases/${caseId}`, {
      method: 'DELETE'
    });
    if (!res.ok && res.status !== 404) throw new Error('Failed to delete case');
  },

  // Evidence
  async getAllEvidence(): Promise<ApiEvidence[]> {
    const res = await fetch(`${API_BASE}/evidence`);
    if (!res.ok) throw new Error('Failed to load evidence');
    return res.json();
  },

  async getCaseEvidence(caseId: string): Promise<ApiEvidence[]> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/evidence`);
    if (!res.ok) throw new Error('Failed to load case evidence');
    return res.json();
  },

  async uploadEvidence(
    caseId: string,
    files: File[],
    notesMap?: Record<string, string>
  ): Promise<ApiEvidence[]> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    if (notesMap && Object.keys(notesMap).length > 0) {
      formData.append('notes_map', JSON.stringify(notesMap));
    }

    const res = await fetch(`${API_BASE}/cases/${caseId}/evidence`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      let errorMsg = 'Failed to upload evidence';
      try {
        const err = await res.json();
        if (err.detail) errorMsg = err.detail;
      } catch (e) {}
      throw new Error(errorMsg);
    }

    return res.json();
  },

  async deleteEvidence(evidenceId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/evidence/${evidenceId}`, {
      method: 'DELETE'
    });
    if (!res.ok && res.status !== 404) throw new Error('Failed to delete evidence');
  },

  getFileUrl(evidenceId: string): string {
    return `${API_BASE}/evidence/${evidenceId}/file`;
  },

  // Extraction
  async triggerExtraction(evidenceId: string): Promise<ApiEvidence> {
    const res = await fetch(`${API_BASE}/evidence/${evidenceId}/extract`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to run evidence extraction');
    return res.json();
  },

  async extractAllCaseEvidence(caseId: string): Promise<ApiEvidence[]> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/extract-all`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to run batch extraction');
    return res.json();
  },

  // Entity Intelligence & Cross-Evidence Matching
  async getCaseEntities(caseId: string) {
    const res = await fetch(`${API_BASE}/cases/${caseId}/entities`);
    if (!res.ok) throw new Error('Failed to load case entities');
    return res.json();
  },

  async matchCaseEntities(caseId: string) {
    const res = await fetch(`${API_BASE}/cases/${caseId}/entities/match`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to run entity matching');
    return res.json();
  },

  async reviewEntityMatch(matchId: string, action: 'confirm' | 'reject' | 'separate' | 'undo', notes?: string) {
    const res = await fetch(`${API_BASE}/entities/matches/${matchId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, review_notes: notes })
    });
    if (!res.ok) throw new Error('Failed to submit review');
    return res.json();
  }
};
