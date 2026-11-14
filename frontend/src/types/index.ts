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
  extracted_text?: string | null;
  extraction_confidence?: number | null;
  extraction_metadata?: string | Record<string, any> | null;
  processing_time_ms?: number | null;
}

export interface EntityMention {
  text: string;
  evidence_id: string;
  filename: string;
  confidence: number;
  start_char: number;
  end_char: number;
}

export interface CandidateMatch {
  id: string;
  case_id: string;
  entity_type: string;
  canonical_name: string;
  similarity_score: number;
  status: 'pending' | 'confirmed' | 'rejected' | 'separate';
  mentions: EntityMention[];
  created_at: string;
  reviewed_at?: string | null;
  review_notes?: string | null;
}
