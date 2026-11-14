"""API request/response models (separate from the ORM models and from the AI schemas)."""
import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Decision = Literal["shortlisted", "on_hold", "not_progressing"]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "criterion"


class Criterion(BaseModel):
    key: str | None = None
    label: str = Field(min_length=2, max_length=200)
    weight: float = Field(default=1, ge=0, le=10)
    must_have: bool = False


def _normalise_criteria(criteria: list[Criterion]) -> list[Criterion]:
    seen: set[str] = set()
    for c in criteria:
        key = slugify(c.key or c.label)
        base, n = key, 2
        while key in seen:
            key, n = f"{base}_{n}", n + 1
        c.key = key
        seen.add(key)
    return criteria


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    department: str | None = None
    location: str | None = None
    description: str = Field(min_length=10)
    criteria: list[Criterion] = Field(min_length=1, max_length=20)
    status: Literal["draft", "open", "closed"] = "open"

    @field_validator("criteria")
    @classmethod
    def _keys(cls, v):
        return _normalise_criteria(v)


class JobUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    location: str | None = None
    description: str | None = None
    criteria: list[Criterion] | None = None
    status: Literal["draft", "open", "closed"] | None = None

    @field_validator("criteria")
    @classmethod
    def _keys(cls, v):
        return _normalise_criteria(v) if v is not None else v


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    department: str | None
    location: str | None
    description: str
    criteria: list[dict]
    status: str
    created_at: datetime
    updated_at: datetime
    application_count: int = 0
    analysed_count: int = 0
    processing_count: int = 0


class UploadResult(BaseModel):
    batch_id: uuid.UUID
    accepted: list[dict]
    rejected: list[dict]


class ApplicationSummary(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_name: str | None
    candidate_email: str | None
    status: str
    failure_reason: str | None
    cv_filename: str
    created_at: datetime
    overall_score: float | None
    must_have_met: bool | None
    total_years_experience: float | None
    top_skills: list[str]


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    summary: str | None
    total_years_experience: float | None
    skills: list[dict]
    experience: list[dict]
    education: list[dict]
    certifications: list[str]
    languages: list[str]
    model_name: str
    prompt_version: str


class AssessmentOut(BaseModel):
    overall_score: float
    must_have_met: bool
    score_at_analysis: float
    criteria: list[dict]
    strengths: list[str]
    gaps: list[str]
    interview_questions: list[dict]
    model_name: str
    prompt_version: str
    created_at: datetime


class ReviewIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    decision: Decision
    notes: str | None = Field(default=None, max_length=5000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reviewer: str
    decision: str
    notes: str | None
    created_at: datetime


class ApplicationDetail(BaseModel):
    id: uuid.UUID
    job: dict
    candidate: CandidateOut
    status: str
    failure_reason: str | None
    cv_filename: str
    created_at: datetime
    profile: ProfileOut | None
    assessment: AssessmentOut | None
    reviews: list[ReviewOut]
