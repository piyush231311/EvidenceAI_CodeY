export type EvidenceType = 'image' | 'audio' | 'document' | 'text';

export type CaseStatus = 'Active' | 'Under Review' | 'Archived' | 'Closed';

export interface CaseNote {
  id: string;
  caseId: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

export interface Case {
  id: string;
  title: string;
  description: string;
  status: CaseStatus;
  createdAt: string;
  updatedAt: string;
  evidenceCount?: number;
  priority?: 'Low' | 'Medium' | 'High' | 'Critical';
  tags?: string[];
  notes?: CaseNote[];
}

export interface EvidenceMetadata {
  sha256?: string;
  resolution?: string; // e.g. "1920x1080"
  duration?: string;   // e.g. "02:45"
  bitrate?: string;
  pageCount?: number;
  authorOrSource?: string;
  originalPath?: string;
  mimeType: string;
  authenticityStatus?: 'Verified' | 'Pending' | 'Flagged';
}

export interface EvidenceFile {
  id: string;
  caseId: string;
  fileName: string;
  displayName: string;
  fileType: EvidenceType;
  fileExtension: string;
  fileSize: number; // in bytes
  dateAdded: string;
  notes?: string;
  metadata: EvidenceMetadata;
  previewUrl?: string; // Blob URL or placeholder asset
  fileObject?: File;   // In-memory File for current browser session
  textContent?: string; // For text/chat/json preview
  audioUrl?: string;   // For playable audio
}

export type UploadStatus = 'queued' | 'validating' | 'uploading' | 'completed' | 'error';

export interface StagedUploadItem {
  id: string;
  file: File;
  caseId: string;
  fileType: EvidenceType;
  displayName: string;
  notes: string;
  progress: number;
  status: UploadStatus;
  errorMessage?: string;
  previewUrl?: string;
}

export type ActivityAction = 
  | 'CASE_CREATED' 
  | 'CASE_EDITED' 
  | 'CASE_STATUS_CHANGED' 
  | 'CASE_DELETED'
  | 'EVIDENCE_ADDED' 
  | 'EVIDENCE_REMOVED' 
  | 'EVIDENCE_EDITED'
  | 'NOTE_ADDED' 
  | 'NOTE_UPDATED' 
  | 'NOTE_DELETED';

export interface ActivityRecord {
  id: string;
  caseId: string;
  caseTitle?: string;
  evidenceId?: string;
  evidenceName?: string;
  action: ActivityAction;
  description: string;
  timestamp: string;
  details?: Record<string, any>;
}

export interface StorageInfo {
  totalBytes: number;
  usedBytes: number;
  maxBytes: number;
  fileCount: number;
}

export interface AppSettings {
  theme: 'dark' | 'light';
  reducedMotion: boolean;
  density: 'comfortable' | 'compact';
  activeCaseId: string;
}
