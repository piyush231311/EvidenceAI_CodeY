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
  confidence: number;                      // GLiNER classification confidence
  ocr_confidence?: number | null;          // Source OCR/ASR extraction confidence
  start_char: number;
  end_char: number;
  source_segment_id?: string | null;
  is_low_confidence?: boolean;
  requires_source_verification?: boolean;
  quality_flags?: string[];
}

export interface EntityRelationship {
  target_canonical_name: string;
  target_match_id?: string;
  relationship_type: string;
  rationale: string;
}

export interface CandidateMatch {
  id: string;
  case_id: string;
  entity_type: string;
  canonical_name: string;
  similarity_score: number;                // RapidFuzz similarity score
  classification_confidence?: number;      // GLiNER classification confidence
  ocr_confidence?: number | null;          // Source OCR recognition confidence
  extraction_confidence?: number;
  status: 'pending' | 'confirmed' | 'rejected' | 'separate';
  mentions: EntityMention[];
  is_single_occurrence?: boolean;
  is_low_confidence?: boolean;
  requires_source_verification?: boolean;
  verification_reasons?: string[];
  related_entities?: EntityRelationship[];
  match_type?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  review_notes?: string | null;
}

export interface EventCandidate {
  id: string;
  case_id: string;
  event_type: string;
  title: string;
  description: string;
  actors: string[];
  action: string;
  location?: string | null;
  original_time_expression?: string | null;
  normalized_start_time?: string | null;
  temporal_precision: string;
  evidence_ids: string[];
  source_segment_ids: string[];
  supporting_text_spans: string[];
  modality: 'completed' | 'planned' | 'alleged' | 'denied' | string;
  explicit_or_inferred: string;
  uncertainty_flags: string[];
  validation_status: string;
  review_status: string;
  created_at: string;
}

export interface TimelineEntry {
  entry_id: string;
  event_id: string;
  case_id: string;
  title: string;
  description: string;
  event_type: string;
  actors: string[];
  action: string;
  location?: string | null;
  original_time_expression?: string | null;
  timestamp?: string | null;
  datetime?: string | null;
  datetime_formatted?: string | null;
  source_filename?: string | null;
  temporal_precision: string;
  is_unscheduled: boolean;
  timeline_status: 'supported_by_evidence' | 'corroborated' | 'conflicting_evidence' | 'user_clarified' | string;
  evidence_ids: string[];
  supporting_text_spans: string[];
  contradictions: Array<Record<string, any>>;
  modality: string;
}

export interface TimelineData {
  case_id: string;
  scheduled_events: TimelineEntry[];
  unscheduled_events: TimelineEntry[];
  total_events_count: number;
  corroborated_count: number;
  conflicting_count: number;
  reconstructed_at: string;
}

export interface ContradictionRecord {
  id: string;
  case_id: string;
  contradiction_type: string;
  description: string;
  event_ids: string[];
  evidence_ids: string[];
  statement_a: string;
  statement_b: string;
  source_a: string;
  source_b: string;
  unresolved_question: string;
  resolution_status: string;
  created_at: string;
}

export interface PreliminaryCaseUnderstanding {
  case_id: string;
  narrative_summary: string;
  key_parties: Array<{
    name: string;
    entity_type: string;
    mentions: number;
    sources: string[];
  }>;
  established_facts: Array<{
    fact_statement: string;
    timestamp?: string;
    actors?: string[];
    evidence_title?: string;
    evidence_id?: string;
    excerpt?: string;
  }>;
  proposed_or_planned: Array<{
    activity: string;
    proposed_time?: string;
    actors?: string[];
    status?: string;
    evidence_title?: string;
    evidence_id?: string;
    excerpt?: string;
  }>;
  claims_and_allegations: Array<{
    claim: string;
    asserting_party?: string;
    target_activity?: string;
    evidence_title?: string;
    evidence_id?: string;
    excerpt?: string;
  }>;
  unclear_or_disputed: Array<{
    contradiction_id?: string;
    issue: string;
    contradiction_type?: string;
    sources_involved?: string[];
    severity?: string;
  }>;
  evidence_sources: Array<{
    evidence_id: string;
    filename: string;
    file_type: string;
  }>;
}

export interface ClarificationQuestion {
  id: string;
  case_id: string;
  event_id?: string | null;
  contradiction_id?: string | null;
  question_type: string;
  activity_name?: string;
  prompt?: string;
  question_text?: string;
  why_it_matters?: string;
  context_summary?: string;
  context_excerpt?: string;
  options: string[];
  status?: 'unanswered' | 'answered' | 'skipped' | string;
  created_at?: string;
}

export interface SubmitAnswerPayload {
  question_id: string;
  selected_option: string;
  free_text_clarification?: string;
  user_surety: 'Very sure' | 'Fairly sure' | 'Somewhat sure' | 'Unsure' | 'Do not remember' | string;
  knowledge_basis: 'Not specified' | 'Directly witnessed' | 'Personally participated' | 'Heard from another person' | 'Inferred' | 'Document review only' | string;
}

export interface UserAnswer {
  id: string;
  question_id: string;
  case_id: string;
  event_id?: string | null;
  selected_option: string;
  free_text_clarification?: string | null;
  user_surety: string;
  surety_score: number;
  knowledge_basis: string;
  submitted_at: string;
}

export interface ReportResponse {
  id: string;
  case_id: string;
  report_data: Record<string, any>;
  html_preview: string;
  created_at: string;
}

export interface FactClaim {
  claim_id: string;
  topic: string;
  claim_text: string;
  citation: {
    evidence_id: string;
    filename: string;
    verbatim_quote: string;
    timestamp_or_date?: string | null;
  };
  category: string;
}

export interface MVPCaseAnalysis {
  id: string;
  case_id: string;
  case_title: string;
  case_domain: string;
  preliminary_narrative: string;
  narrative_word_count: number;
  evidence_backed_facts: FactClaim[];
  unresolved_questions: ClarificationQuestion[];
  timeline_status: 'available' | 'unavailable' | 'partial' | string;
  scheduled_events_count: number;
  unscheduled_events_count: number;
  inference_source: string;
  generated_at: string;
}
