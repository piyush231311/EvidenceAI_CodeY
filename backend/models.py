import uuid
from datetime import datetime
from typing import Optional, Any, List, Dict
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict, Field
from .db import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    file_type = Column(String(32), nullable=False)  # 'image' | 'audio' | 'text'
    mime_type = Column(String(128), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    authenticity_passed = Column(Boolean, default=True, nullable=False)
    authenticity_score = Column(Float, nullable=True)
    review_status = Column(String(32), default="INCLUDED", nullable=False)
    quarantine_reason = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    extracted_text = Column(Text, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    extraction_metadata = Column(Text, nullable=True)
    processing_time_ms = Column(Float, nullable=True)

    case = relationship("Case", back_populates="evidence_items")


class AuditLog(Base):
    """
    Append-only audit log: never update or delete rows.
    Tracks every upload and action for forensic integrity.
    """
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), nullable=False, index=True)
    evidence_id = Column(String(36), nullable=True, index=True)
    action = Column(String(64), nullable=False)  # e.g. "UPLOADED"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    details = Column(Text, nullable=True)  # JSON-encoded payload details


class EntityMatchRecord(Base):
    """
    Stores cross-evidence candidate entity matches and their human review status.
    Never automatically merges personas.
    """
    __tablename__ = "entity_matches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False)
    canonical_name = Column(String(255), nullable=False)
    similarity_score = Column(Float, nullable=False)
    is_single_occurrence = Column(Boolean, default=False, nullable=True)
    classification_confidence = Column(Float, default=1.0, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    extraction_confidence = Column(Float, default=1.0, nullable=True)
    is_low_confidence = Column(Boolean, default=False, nullable=True)
    requires_source_verification = Column(Boolean, default=False, nullable=True)
    verification_reasons_json = Column(Text, nullable=True)
    related_entities_json = Column(Text, nullable=True)
    match_type = Column(String(64), nullable=True)
    status = Column(String(32), default="pending", nullable=False)  # pending | confirmed | rejected | separate
    mentions_json = Column(Text, nullable=False)                     # JSON serialized mentions list
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)


class EventRecord(Base):
    """Stores extracted event candidates with source citations and modality."""
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    actors_json = Column(Text, nullable=False)
    action = Column(String(128), nullable=False)
    location = Column(String(128), nullable=True)
    original_time_expression = Column(String(128), nullable=True)
    normalized_start_time = Column(DateTime, nullable=True)
    temporal_precision = Column(String(32), default="unknown")
    evidence_ids_json = Column(Text, nullable=False)
    source_segment_ids_json = Column(Text, nullable=False)
    supporting_text_spans_json = Column(Text, nullable=False)
    modality = Column(String(32), default="completed")
    explicit_or_inferred = Column(String(64), default="explicit_statement")
    uncertainty_flags_json = Column(Text, nullable=True)
    validation_status = Column(String(32), default="valid")
    review_status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EventContradictionRecord(Base):
    """Stores detected discrepancies and contradictions across evidence accounts."""
    __tablename__ = "contradictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    contradiction_type = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    event_ids_json = Column(Text, nullable=False)
    evidence_ids_json = Column(Text, nullable=False)
    statement_a = Column(Text, nullable=False)
    statement_b = Column(Text, nullable=False)
    source_a = Column(String(128), nullable=False)
    source_b = Column(String(128), nullable=False)
    unresolved_question = Column(Text, nullable=False)
    resolution_status = Column(String(32), default="unresolved")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClarificationQuestionRecord(Base):
    """Stores focused quiz questions derived from real case ambiguities."""
    __tablename__ = "clarification_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    event_id = Column(String(36), nullable=True)
    contradiction_id = Column(String(36), nullable=True)
    question_type = Column(String(64), nullable=False)
    activity_name = Column(String(128), nullable=True, default="")
    prompt = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=True, default="")
    context_excerpt = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    status = Column(String(32), default="unanswered")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserAnswerRecord(Base):
    """Stores investigator/witness clarification responses with self-reported surety."""
    __tablename__ = "user_answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("clarification_questions.id"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    event_id = Column(String(36), nullable=True)
    selected_option = Column(Text, nullable=False)
    free_text_clarification = Column(Text, nullable=True)
    user_surety = Column(String(32), nullable=False)
    surety_score = Column(Integer, nullable=False)
    knowledge_basis = Column(String(64), nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    version = Column(Integer, default=1)


class ReconstructedReportRecord(Base):
    """Stores comprehensive reconstructed forensic incident reports."""
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    report_json = Column(Text, nullable=False)
    html_preview = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MVPAnalysisRecord(Base):
    """Stores streamlined core MVP case analysis (preliminary story, facts, questions)."""
    __tablename__ = "mvp_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AnalysisJobRecord(Base):
    """Persistent background analysis job tracking the 15-stage pipeline."""
    __tablename__ = "analysis_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    pipeline_version = Column(String(32), default="2.0.0", nullable=False)
    policy_mode = Column(String(32), default="DEVELOPMENT", nullable=False)  # DEVELOPMENT | STRICT_REVIEW
    policy_version = Column(String(16), default="1.0.0", nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True)  # PENDING | RUNNING | WAITING_FOR_USER | COMPLETED | FAILED
    current_stage = Column(String(64), default="VALIDATE_EVIDENCE", nullable=False)
    evidence_hashes_json = Column(Text, default="[]", nullable=False)
    completed_stages_json = Column(Text, default="[]", nullable=False)
    failed_stage = Column(String(64), nullable=True)
    error_details = Column(Text, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_time = Column(DateTime, nullable=True)
    artifacts_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AnalysisStageRecord(Base):
    """Durable state for each of the 15 pipeline stages in an analysis job."""
    __tablename__ = "analysis_job_stages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    stage_name = Column(String(64), nullable=False)
    order_index = Column(Integer, nullable=False)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING | RUNNING | COMPLETED | FAILED | SKIPPED | WAITING_FOR_USER
    start_time = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    details_json = Column(Text, default="{}", nullable=False)
    error_message = Column(Text, nullable=True)


# Pydantic Response Schemas
class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    original_filename: str
    stored_path: str
    file_type: str
    mime_type: str
    size_bytes: int
    sha256: str
    notes: Optional[str] = None
    authenticity_passed: bool
    authenticity_score: Optional[float] = None
    review_status: str = "INCLUDED"
    quarantine_reason: Optional[str] = None
    uploaded_at: datetime
    extracted_text: Optional[str] = None
    extraction_confidence: Optional[float] = None
    extraction_metadata: Optional[Any] = None
    processing_time_ms: Optional[float] = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    evidence_id: Optional[str] = None
    action: str
    timestamp: datetime
    details: Optional[Any] = None


class EntityMentionSchema(BaseModel):
    text: str
    evidence_id: str
    filename: str
    confidence: float                       # GLiNER classification confidence
    ocr_confidence: Optional[float] = None  # Source OCR/ASR extraction confidence
    start_char: int
    end_char: int
    source_segment_id: Optional[str] = None
    is_low_confidence: bool = False
    requires_source_verification: bool = False
    quality_flags: List[str] = []


class CandidateMatchResponse(BaseModel):
    id: str
    case_id: str
    entity_type: str
    canonical_name: str
    similarity_score: float
    classification_confidence: float = 1.0
    ocr_confidence: Optional[float] = None
    extraction_confidence: float = 1.0
    status: str
    mentions: List[EntityMentionSchema]
    is_single_occurrence: bool = False
    is_low_confidence: bool = False
    requires_source_verification: bool = False
    verification_reasons: List[str] = []
    related_entities: List[Dict[str, Any]] = []
    match_type: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


class ReviewMatchPayload(BaseModel):
    action: str                      # "confirm" | "reject" | "separate" | "undo"
    review_notes: Optional[str] = None


class EventCandidateResponse(BaseModel):
    id: str
    case_id: str
    event_type: str
    title: str
    description: str
    actors: List[str]
    action: str
    location: Optional[str] = None
    original_time_expression: Optional[str] = None
    normalized_start_time: Optional[datetime] = None
    temporal_precision: str
    evidence_ids: List[str]
    source_segment_ids: List[str]
    supporting_text_spans: List[str]
    modality: str
    explicit_or_inferred: str
    uncertainty_flags: List[str] = []
    validation_status: str
    review_status: str
    created_at: datetime


class TimelineEntryResponse(BaseModel):
    entry_id: str
    event_id: str
    case_id: str
    title: str
    description: str
    event_type: str
    actors: List[str]
    action: str
    location: Optional[str] = None
    original_time_expression: Optional[str] = None
    timestamp: Optional[datetime] = None
    temporal_precision: str
    is_unscheduled: bool
    timeline_status: str
    evidence_ids: List[str]
    supporting_text_spans: List[str]
    contradictions: List[Dict[str, Any]] = []
    modality: str


class TimelineResponse(BaseModel):
    case_id: str
    scheduled_events: List[TimelineEntryResponse]
    unscheduled_events: List[TimelineEntryResponse]
    total_events_count: int
    corroborated_count: int
    conflicting_count: int
    reconstructed_at: datetime


class ContradictionResponse(BaseModel):
    id: str
    case_id: str
    contradiction_type: str
    description: str
    event_ids: List[str]
    evidence_ids: List[str]
    statement_a: str
    statement_b: str
    source_a: str
    source_b: str
    unresolved_question: str
    resolution_status: str
    created_at: datetime


class PreliminaryCaseUnderstandingResponse(BaseModel):
    case_id: str
    narrative_summary: str
    key_parties: List[Dict[str, Any]]
    established_facts: List[Dict[str, Any]]
    proposed_or_planned: List[Dict[str, Any]]
    claims_and_allegations: List[Dict[str, Any]]
    unclear_or_disputed: List[Dict[str, Any]]
    evidence_sources: List[Dict[str, Any]]


class ClarificationQuestionResponse(BaseModel):
    id: str
    case_id: str
    event_id: Optional[str] = None
    contradiction_id: Optional[str] = None
    question_type: str
    activity_name: Optional[str] = ""
    prompt: str
    why_it_matters: Optional[str] = ""
    context_excerpt: str
    options: List[str]
    status: str
    created_at: datetime


class SubmitAnswerPayload(BaseModel):
    question_id: str
    selected_option: str
    free_text_clarification: Optional[str] = None
    user_surety: str = "Fairly sure"     # Very sure | Fairly sure | Somewhat sure | Unsure | Do not remember
    knowledge_basis: str = "Not specified"  # Default: Not specified


class UserAnswerResponse(BaseModel):
    id: str
    question_id: str
    case_id: str
    event_id: Optional[str] = None
    selected_option: str
    free_text_clarification: Optional[str] = None
    user_surety: str
    surety_score: int
    knowledge_basis: str
    submitted_at: datetime


class ReportResponse(BaseModel):
    id: str
    case_id: str
    report_data: Dict[str, Any]
    html_preview: str
    created_at: datetime


class MVPCaseAnalysisResponse(BaseModel):
    id: str
    case_id: str
    case_title: str
    case_domain: str
    brief_summary: str = ""
    brief_summary_word_count: int = 0
    preliminary_narrative: str
    narrative_word_count: int
    evidence_backed_facts: List[Dict[str, Any]]
    unresolved_questions: List[Dict[str, Any]]
    relevant_participants: List[Dict[str, str]] = Field(default_factory=list)
    visual_findings: List[Dict[str, Any]] = Field(default_factory=list)
    significant_communications: List[Dict[str, Any]] = Field(default_factory=list)
    attributed_claims: List[Dict[str, Any]] = Field(default_factory=list)
    vision_enabled: bool = True
    vision_status_summary: str = "not_applicable"
    authenticity_assessments: List[Dict[str, Any]] = Field(default_factory=list)
    authenticity_status_summary: str = "not_applicable"
    timeline_status: str
    scheduled_events_count: int
    unscheduled_events_count: int
    inference_source: str
    generated_at: datetime


class AnalysisStageResponse(BaseModel):
    id: str
    job_id: str
    stage_name: str
    order_index: int
    status: str
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class AnalysisJobResponse(BaseModel):
    id: str
    case_id: str
    pipeline_version: str
    policy_mode: str = "DEVELOPMENT"
    policy_version: str = "1.0.0"
    status: str
    current_stage: str
    progress_percentage: int
    completed_stages: List[str]
    failed_stage: Optional[str] = None
    error_details: Optional[str] = None
    start_time: datetime
    completion_time: Optional[datetime] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    stages: Optional[List[AnalysisStageResponse]] = None
    created_at: datetime
    updated_at: datetime
