export interface Case {
  id: string;
  created_at: string;
  evidence_count?: number;
}

export interface EvidenceFile {
  id: string;
  case_id: string;
  original_filename: string;
  stored_path: string;
  file_type: 'image' | 'audio' | 'text' | string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  notes: string | null;
  authenticity_passed: boolean;
  authenticity_score: number | null;
  uploaded_at: string;
}
