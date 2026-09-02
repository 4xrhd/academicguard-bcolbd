"""
schemas.py — Pydantic v2 request/response models (API contract).
All request bodies are validated here; no raw SQL interpolation.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Marking Configurations (FR-MARK-03) ──────────────────────────────────────

class MarkingConfigTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    total_marks: float = Field(..., gt=0)
    config_data: dict = Field(...)
    is_default: bool = False

class MarkingConfigTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    total_marks: Optional[float] = Field(None, gt=0)
    config_data: Optional[dict] = None
    is_default: Optional[bool] = None

class MarkingConfigTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    total_marks: float
    config_data: dict
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Batches ───────────────────────────────────────────────────────────────────

class BatchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    course_code: str = Field(..., min_length=1, max_length=50)


class MarkingThreshold(BaseModel):
    """Threshold range and mark deduction for a feature"""
    min_value: float = Field(..., ge=0, le=100)
    max_value: float = Field(..., ge=0, le=100)
    marks_deduct: float = Field(..., ge=0)

    @model_validator(mode="after")
    def check_range(self):
        if self.min_value > self.max_value:
            raise ValueError(f"min_value ({self.min_value}) must be <= max_value ({self.max_value})")
        return self


class MarkingConfig(BaseModel):
    """Marking configuration for a batch"""
    total_marks: float = Field(..., gt=0)
    ai_thresholds: list[MarkingThreshold]  # AI detection thresholds
    text_copy_thresholds: list[MarkingThreshold]  # Text similarity thresholds
    code_ast_thresholds: list[MarkingThreshold]  # Code AST thresholds
    risk_score_thresholds: list[MarkingThreshold]  # Risk score thresholds


class BatchResponse(BaseModel):
    id: uuid.UUID
    name: str
    course_code: str
    status: str
    progress: float
    uploaded_at: datetime
    completed_at: Optional[datetime]
    submission_count: int = 0
    total_marks: Optional[float] = None
    marking_config: Optional[dict] = None

    model_config = {"from_attributes": True}


class BatchStatusResponse(BaseModel):
    batch_id: uuid.UUID
    status: str    # pending | processing | done | error
    progress: float  # 0–100


# ── Submissions ───────────────────────────────────────────────────────────────

class SubmissionResponse(BaseModel):
    id: uuid.UUID
    student_id: Optional[str]
    student_name: Optional[str]
    parse_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionDetailResponse(SubmissionResponse):
    raw_text: Optional[str]
    code_blocks: Optional[list[str]]
    ai_result: Optional["AIDetectionResponse"]
    risk_score: Optional["RiskScoreResponse"]
    similarity_pairs: list["SimilarityPairResponse"] = []
    marks_obtained: Optional[float] = None
    marks_breakdown: Optional[dict] = None


# ── Similarity ────────────────────────────────────────────────────────────────

class SimilarityPairResponse(BaseModel):
    id: uuid.UUID
    sub_a_id: uuid.UUID
    sub_b_id: uuid.UUID
    tfidf_score: float
    semantic_score: float
    text_sim_fused: float
    code_ast_score: float
    copy_direction: str
    other_student_name: Optional[str] = None
    other_student_id: Optional[str] = None

    model_config = {"from_attributes": True}


class HeatmapResponse(BaseModel):
    student_ids: list[str]
    matrix: list[list[float]]   # N×N fused text similarity scores


# ── AI Detection ──────────────────────────────────────────────────────────────

class AIDetectionResponse(BaseModel):
    perplexity_score: Optional[float]
    burstiness_score: Optional[float]
    stylometric_score: Optional[float]
    api_score: Optional[float]
    final_ai_prob: float
    source: str

    model_config = {"from_attributes": True}


# ── Risk Scores ───────────────────────────────────────────────────────────────

class RiskScoreResponse(BaseModel):
    text_sim_max: float
    code_sim_max: Optional[float]
    ai_prob: float
    weighted_score: float
    risk_level: str    # low | medium | high
    weight_profile: str

    model_config = {"from_attributes": True}


# ── Batch Results (full dashboard data) ───────────────────────────────────────

class StudentRiskRow(BaseModel):
    submission_id: uuid.UUID
    student_id: Optional[str]
    student_name: Optional[str]
    risk_level: str
    weighted_score: float
    ai_prob: float
    text_sim_max: float
    code_sim_max: Optional[float]
    marks_obtained: Optional[float] = None
    marks_breakdown: Optional[dict] = None


class BatchResultsResponse(BaseModel):
    batch: BatchResponse
    risk_ranking: list[StudentRiskRow]   # Sorted descending by weighted_score
    heatmap: HeatmapResponse


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    format: str
    generated_at: datetime

    model_config = {"from_attributes": True}


# ── Admin ─────────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[uuid.UUID]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[uuid.UUID]
    ip_address: Optional[str]
    timestamp: datetime

    @field_validator("ip_address", mode="before")
    @classmethod
    def cast_ip(cls, v):
        return str(v) if v else None

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    user_id: Optional[uuid.UUID] = None
    action: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ── Annotations ───────────────────────────────────────────────────────────────

class AnnotationCreate(BaseModel):
    label: str = Field(..., pattern="^(human|ai_generated|plagiarized|mixed)$")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


class AnnotationUpdate(BaseModel):
    label: Optional[str] = Field(None, pattern="^(human|ai_generated|plagiarized|mixed)$")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    notes: Optional[str] = None


class AnnotationResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    user_id: uuid.UUID
    label: str
    confidence: float
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnnotationBulkItem(BaseModel):
    submission_id: uuid.UUID
    label: str = Field(..., pattern="^(human|ai_generated|plagiarized|mixed)$")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


class AnnotationBulkCreate(BaseModel):
    annotations: list[AnnotationBulkItem]


# ── Training Runs ─────────────────────────────────────────────────────────────

class TrainingRunResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    status: str
    samples_count: int = 0
    accuracy: Optional[float] = None
    roc_auc: Optional[float] = None
    f1_score: Optional[float] = None
    precision_score: Optional[float] = None
    recall_score: Optional[float] = None
    model_path: Optional[str] = None
    is_active: bool = False
    training_config: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TrainingStatsResponse(BaseModel):
    total_annotations: int
    label_distribution: dict[str, int]
    binary_distribution: dict[str, int]
    min_samples_required: int
    min_per_class_required: int
    ready_to_train: bool


# Update forward references
SubmissionDetailResponse.model_rebuild()
