"""
models.py — SQLAlchemy ORM models for all 8 core database tables.

Tables:
    users, batches, submissions, similarity_results,
    ai_detection_results, risk_scores, reports, audit_logs
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional, Dict

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, Float,
    ForeignKey, Index, String, Text, func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.session import Base

# ── Helpers ───────────────────────────────────────────────────────────────────

def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

def now_utc() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── 1. users ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("instructor", "admin", name="user_role"), nullable=False, default="instructor")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = now_utc()

    batches: Mapped[list["Batch"]] = relationship("Batch", back_populates="instructor", lazy="select")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="select")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", lazy="select", cascade="all, delete-orphan")
    marking_configs: Mapped[list["MarkingConfigTemplate"]] = relationship("MarkingConfigTemplate", back_populates="user", lazy="select", cascade="all, delete-orphan")


class RefreshToken(Base):
    """Stored refresh tokens for rotation and revocation (FR-AUTH-04)."""
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = now_utc()

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
    )


# ── 2. batches ────────────────────────────────────────────────────────────────

class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False)
    instructor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "done", "error", name="batch_status"),
        nullable=False, default="pending"
    )
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)   # 0–100
    uploaded_at: Mapped[datetime] = now_utc()
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Marking configuration (FR-MARK-01) - Updated
    total_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Total marks for assignment
    marking_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Thresholds & deductions per feature

    instructor: Mapped["User"] = relationship("User", back_populates="batches")
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="batch", lazy="select", cascade="all, delete-orphan", passive_deletes=True)
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="batch", lazy="select", cascade="all, delete-orphan", passive_deletes=True)
    similarity_results: Mapped[list["SimilarityResult"]] = relationship("SimilarityResult", back_populates="batch", lazy="select", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("ix_batches_instructor_id", "instructor_id"),
        Index("ix_batches_uploaded_at", "uploaded_at"),
    )


# ── 3. submissions ────────────────────────────────────────────────────────────

class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)    # Extracted from cover page; null if parse_error
    student_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)          # SHA-256-hashed filename path
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)           # Theory text body
    code_blocks: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)          # Array of extracted code strings
    parse_status: Mapped[str] = mapped_column(
        Enum("ok", "parse_error", name="parse_status"),
        nullable=False, default="ok"
    )
    
    # Marking (FR-MARK-02)
    marks_obtained: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Final marks after deductions
    marks_breakdown: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Deductions per feature
    
    created_at: Mapped[datetime] = now_utc()

    @property
    def has_code(self) -> bool:
        return bool(self.code_blocks and len(self.code_blocks) > 0)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="submissions")
    ai_result: Mapped[Optional["AIDetectionResult"]] = relationship("AIDetectionResult", back_populates="submission", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    risk_score: Mapped[Optional["RiskScore"]] = relationship("RiskScore", back_populates="submission", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    annotation: Mapped[Optional["Annotation"]] = relationship("Annotation", back_populates="submission", uselist=False, cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("ix_submissions_batch_student", "batch_id", "student_id"),
    )


# ── 4. similarity_results ─────────────────────────────────────────────────────

class SimilarityResult(Base):
    __tablename__ = "similarity_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    sub_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    sub_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    tfidf_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    text_sim_fused: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)   # 0.4×tfidf + 0.6×semantic
    code_ast_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    copy_direction: Mapped[str] = mapped_column(
        Enum("a_to_b", "b_to_a", "mutual", "unknown", name="copy_direction"),
        nullable=False, default="unknown"
    )

    batch: Mapped["Batch"] = relationship("Batch", back_populates="similarity_results")

    __table_args__ = (
        Index("ix_sim_results_batch", "batch_id"),
        Index("ix_sim_results_pair", "sub_a_id", "sub_b_id"),
    )


# ── 5. ai_detection_results ───────────────────────────────────────────────────

class AIDetectionResult(Base):
    __tablename__ = "ai_detection_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    perplexity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    burstiness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stylometric_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    api_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # GPTZero score (optional)
    final_ai_prob: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)   # 0.0–1.0
    source: Mapped[str] = mapped_column(
        Enum("local", "gptzero", "fused", name="ai_source"),
        nullable=False, default="local"
    )

    submission: Mapped["Submission"] = relationship("Submission", back_populates="ai_result")


# ── 6. risk_scores ────────────────────────────────────────────────────────────

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    text_sim_max: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    code_sim_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    ai_prob: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", name="risk_level"),
        nullable=False, default="low"
    )
    weight_profile: Mapped[str] = mapped_column(String(20), nullable=False, default="code_present")

    submission: Mapped["Submission"] = relationship("Submission", back_populates="risk_score")


# ── 7. reports ────────────────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(
        Enum("pdf", "excel", "csv", "json", name="report_format"),
        nullable=False
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    generated_at: Mapped[datetime] = now_utc()

    batch: Mapped["Batch"] = relationship("Batch", back_populates="reports")

    __table_args__ = (
        Index("ix_reports_batch_id", "batch_id"),
        Index("ix_reports_generated_by", "generated_by"),
    )


# ── 8. audit_logs ─────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable audit log. The application DB user must NOT have DELETE
    permission on this table (FR-AUDIT-01, NFR-SEC-09).
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "batch.upload", "auth.login"
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)     # e.g. "batch", "submission"
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_ts", "user_id", "timestamp"),
        Index("ix_audit_logs_action",  "action"),
    )


# ── 9. annotations ───────────────────────────────────────────────────────────

class Annotation(Base):
    """Ground-truth label assigned by an instructor for model training."""
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(
        Enum("human", "ai_generated", "plagiarized", "mixed", name="annotation_label"),
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = now_utc()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    submission: Mapped["Submission"] = relationship("Submission", back_populates="annotation")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_annotations_label", "label"),
    )


# ── 10. training_runs ────────────────────────────────────────────────────────

class TrainingRun(Base):
    """Record of a model training execution with metrics and status."""
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "completed", "failed", name="training_status"),
        nullable=False, default="pending"
    )
    samples_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roc_auc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    training_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = now_utc()
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User")


# ── 11. marking_configs ─────────────────────────────────────────────────────

class MarkingConfigTemplate(Base):
    """Saved templates for marking configurations (FR-MARK-03)."""
    __tablename__ = "marking_configs"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # The actual config data (matches Batch.marking_config structure)
    total_marks: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    config_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = now_utc()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="marking_configs")
