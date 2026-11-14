// Evidence AI - Direct Backend API Service (Zero Mock Data)

export interface ApiCase {
  id: string;
  created_at: string;
  evidence_count?: number;
}

export interface ApiAnalysisStage {
  id: string;
  job_id: string;
  stage_name: string;
  order_index: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'WAITING_FOR_USER' | 'SKIPPED';
  start_time: string | null;
  completion_time: string | null;
  duration_ms: number | null;
  details: Record<string, any>;
  error_message: string | null;
}

export interface ApiAnalysisJob {
  id: string;
  case_id: string;
  pipeline_version: string;
  status: 'PENDING' | 'RUNNING' | 'WAITING_FOR_USER' | 'COMPLETED' | 'FAILED';
  current_stage: string;
  progress_percentage: number;
  completed_stages: string[];
  failed_stage: string | null;
  error_details: string | null;
  start_time: string;
  completion_time: string | null;
  artifacts: Record<string, any>;
  stages?: ApiAnalysisStage[];
  created_at: string;
  updated_at: string;
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

export interface User {
  id: string;
  username: string;
  created_at: string;
}

export interface AuthResponse {
  user: User;
  recovery_codes?: string[] | null;
}

const API_BASE = '/api';

/**
 * Standardized fetch wrapper that includes credentials and CSRF header
 */
export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});

  const method = (init.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    headers.set('X-Requested-With', 'evidence-ai');
  }

  const response = await fetch(input, {
    ...init,
    credentials: 'include',
    headers
  });

  if (response.status === 401) {
    const urlStr = typeof input === 'string' ? input : input.toString();
    // Do not dispatch global unauthorized redirect when checking initial /api/auth/me
    if (!urlStr.includes('/api/auth/me')) {
      window.dispatchEvent(new CustomEvent('evidence-ai-unauthorized'));
    }
  }

  return response;
}

export const api = {
  // Authentication & Account
  auth: {
    async getMe(): Promise<User> {
      const res = await apiFetch(`${API_BASE}/auth/me`);
      if (!res.ok) throw new Error('Not authenticated');
      return res.json();
    },

    async register(username: string, password: string): Promise<AuthResponse> {
      const res = await apiFetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (!res.ok) {
        let msg = 'Registration failed';
        try {
          const err = await res.json();
          if (err.detail) msg = err.detail;
        } catch (e) {}
        throw new Error(msg);
      }
      return res.json();
    },

    async login(username: string, password: string): Promise<AuthResponse> {
      const res = await apiFetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (!res.ok) {
        let msg = "Username or password didn't match. Please try again.";
        try {
          const err = await res.json();
          if (err.detail) msg = err.detail;
        } catch (e) {}
        throw new Error(msg);
      }
      return res.json();
    },

    async logout(allDevices: boolean = false): Promise<void> {
      await apiFetch(`${API_BASE}/auth/logout?all_devices=${allDevices}`, {
        method: 'POST'
      });
    },

    async changePassword(currentPassword: string, newPassword: string): Promise<{ detail: string }> {
      const res = await apiFetch(`${API_BASE}/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });
      if (!res.ok) {
        let msg = 'Failed to change password';
        try {
          const err = await res.json();
          if (err.detail) msg = err.detail;
        } catch (e) {}
        throw new Error(msg);
      }
      return res.json();
    },

    async recover(username: string, recoveryCode: string, newPassword: string): Promise<AuthResponse> {
      const res = await apiFetch(`${API_BASE}/auth/recover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          recovery_code: recoveryCode,
          new_password: newPassword
        })
      });
      if (!res.ok) {
        let msg = 'Recovery failed';
        try {
          const err = await res.json();
          if (err.detail) msg = err.detail;
        } catch (e) {}
        throw new Error(msg);
      }
      return res.json();
    },

    async regenerateRecoveryCodes(password: string): Promise<string[]> {
      const res = await apiFetch(`${API_BASE}/auth/recovery-codes/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      if (!res.ok) {
        let msg = 'Failed to regenerate recovery codes';
        try {
          const err = await res.json();
          if (err.detail) msg = err.detail;
        } catch (e) {}
        throw new Error(msg);
      }
      const data = await res.json();
      return data.recovery_codes;
    }
  },

  // Cases
  async getCases(): Promise<ApiCase[]> {
    const res = await apiFetch(`${API_BASE}/cases`);
    if (!res.ok) throw new Error('Failed to load cases');
    return res.json();
  },

  async createCase(caseId?: string): Promise<ApiCase> {
    const res = await apiFetch(`${API_BASE}/cases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(caseId ? { id: caseId } : {})
    });
    if (!res.ok) throw new Error('Failed to create case');
    return res.json();
  },

  async deleteCase(caseId: string): Promise<void> {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}`, {
      method: 'DELETE'
    });
    if (!res.ok && res.status !== 404) throw new Error('Failed to delete case');
  },

  // Evidence
  async getAllEvidence(): Promise<ApiEvidence[]> {
    const res = await apiFetch(`${API_BASE}/evidence`);
    if (!res.ok) throw new Error('Failed to load evidence');
    return res.json();
  },

  async getCaseEvidence(caseId: string): Promise<ApiEvidence[]> {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/evidence`);
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

    const res = await apiFetch(`${API_BASE}/cases/${caseId}/evidence`, {
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
    const res = await apiFetch(`${API_BASE}/evidence/${evidenceId}`, {
      method: 'DELETE'
    });
    if (!res.ok && res.status !== 404) throw new Error('Failed to delete evidence');
  },

  getFileUrl(evidenceId: string): string {
    return `${API_BASE}/evidence/${evidenceId}/file`;
  },

  // Extraction
  async triggerExtraction(evidenceId: string): Promise<ApiEvidence> {
    const res = await apiFetch(`${API_BASE}/evidence/${evidenceId}/extract`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to run evidence extraction');
    return res.json();
  },

  async extractAllCaseEvidence(caseId: string): Promise<ApiEvidence[]> {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/extract-all`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to run batch extraction');
    return res.json();
  },

  // Entity Intelligence & Cross-Evidence Matching
  async getCaseEntities(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/entities`);
    if (!res.ok) throw new Error('Failed to load case entities');
    return res.json();
  },

  async matchCaseEntities(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/entities/match`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to run entity matching');
    return res.json();
  },

  async reviewEntityMatch(matchId: string, action: 'confirm' | 'reject' | 'separate' | 'undo', notes?: string) {
    const res = await apiFetch(`${API_BASE}/entities/matches/${matchId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, review_notes: notes })
    });
    if (!res.ok) throw new Error('Failed to submit review');
    return res.json();
  },

  // Event Extraction & Intelligence
  async extractCaseEvents(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/events/extract`, {
      method: 'POST'
    });
    if (!res.ok) {
      let msg = 'Failed to extract events';
      try {
        const err = await res.json();
        if (err.detail) msg = err.detail;
      } catch (e) {}
      throw new Error(msg);
    }
    return res.json();
  },

  async getCaseEvents(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/events`);
    if (!res.ok) throw new Error('Failed to load case events');
    return res.json();
  },

  // Chronological Timeline & Corroboration
  async getCaseTimeline(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/timeline`);
    if (!res.ok) throw new Error('Failed to load case timeline');
    return res.json();
  },

  async getCaseContradictions(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/contradictions`);
    if (!res.ok) throw new Error('Failed to load contradictions');
    return res.json();
  },

  // Clarification Quiz
  async generateClarificationQuiz(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/quiz/generate`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to generate clarification quiz');
    return res.json();
  },

  async getClarificationQuiz(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/quiz`);
    if (!res.ok) throw new Error('Failed to load quiz');
    return res.json();
  },

  async getCaseUnderstanding(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/understanding`);
    if (!res.ok) throw new Error('Failed to load case understanding');
    return res.json();
  },

  async submitQuizAnswer(caseId: string, payload: {
    question_id: string;
    selected_option: string;
    free_text_clarification?: string;
    user_surety: string;
    knowledge_basis: string;
  }) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/quiz/answers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to submit answer');
    return res.json();
  },

  async triggerReconstruction(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/reconstruct`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to run iterative reconstruction');
    return res.json();
  },

  // Forensic Incident Reporting
  async generateReport(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/report/generate`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to generate incident report');
    return res.json();
  },

  async getReport(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/report`);
    if (res.status === 404) return null; // Expected when report not yet generated
    if (!res.ok) throw new Error('Failed to load report');
    return res.json();
  },

  getReportHtmlUrl(caseId: string): string {
    return `${API_BASE}/cases/${caseId}/report/html`;
  },

  // Streamlined Core MVP Case Analysis
  async analyzeCase(caseId: string): Promise<ApiAnalysisJob> {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/analyze`, {
      method: 'POST'
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || 'Failed to execute case analysis');
    }
    return res.json();
  },

  async getCaseAnalysis(caseId: string) {
    const res = await apiFetch(`${API_BASE}/cases/${caseId}/analysis`);
    if (res.status === 404) return null; // Expected when case not yet analyzed
    if (!res.ok) throw new Error('Failed to load case analysis');
    return res.json();
  },

  // One-Click Orchestrated Pipeline Job API
  async getActiveCaseJob(caseId: string): Promise<ApiAnalysisJob | null> {
    try {
      const res = await apiFetch(`${API_BASE}/cases/${caseId}/analysis/active-job`);
      if (res.status === 404 || !res.ok) return null;
      const data = await res.json();
      return (data && data.id && data.current_stage) ? data : null;
    } catch {
      return null;
    }
  },

  async getAnalysisJob(jobId: string): Promise<ApiAnalysisJob> {
    const res = await apiFetch(`${API_BASE}/analysis/jobs/${jobId}`);
    if (!res.ok) throw new Error('Failed to load analysis job');
    return res.json();
  },

  async getAnalysisJobStages(jobId: string): Promise<ApiAnalysisStage[]> {
    const res = await apiFetch(`${API_BASE}/analysis/jobs/${jobId}/stages`);
    if (!res.ok) throw new Error('Failed to load job stages');
    return res.json();
  },

  async getAnalysisJobResult(jobId: string): Promise<any> {
    const res = await apiFetch(`${API_BASE}/analysis/jobs/${jobId}/result`);
    if (!res.ok) throw new Error('Failed to load job result');
    return res.json();
  },

  async retryAnalysisJob(jobId: string): Promise<ApiAnalysisJob> {
    const res = await apiFetch(`${API_BASE}/analysis/jobs/${jobId}/retry`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to retry analysis job');
    return res.json();
  },

  async getAnalysisJobQuiz(jobId: string): Promise<any[]> {
    const res = await apiFetch(`${API_BASE}/analysis/jobs/${jobId}/quiz`);
    if (!res.ok) throw new Error('Failed to load analysis quiz');
    return res.json();
  },

  async submitAnalysisJobQuiz(jobId: string, answers: any[]): Promise<{ status: string; job: ApiAnalysisJob }> {
    const res = await apiFetch(`${API_BASE}/analysis/jobs/${jobId}/quiz/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers })
    });
    if (!res.ok) throw new Error('Failed to submit clarification answers');
    return res.json();
  }
};
