import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict
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
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    uploaded_at: datetime


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
