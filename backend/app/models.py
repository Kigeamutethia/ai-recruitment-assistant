"""ORM models — mirror database/schema.sql.

Types use generic SQLAlchemy types with a Postgres variant (JSON -> JSONB) so the same models
run on PostgreSQL in Docker and on SQLite in the test suite.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    criteria: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(Text, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="candidate")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(Text, default="received")
    failure_reason: Mapped[str | None] = mapped_column(Text)
    cv_filename: Mapped[str] = mapped_column(Text)
    cv_storage_path: Mapped[str] = mapped_column(Text)
    cv_sha256: Mapped[str] = mapped_column(Text)
    cv_text: Mapped[str | None] = mapped_column(Text)
    upload_batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[Job] = relationship(back_populates="applications")
    candidate: Mapped[Candidate] = relationship(back_populates="applications")
    profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="Assessment.created_at.desc()"
    )
    reviews: Mapped[list["RecruiterReview"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="RecruiterReview.created_at.desc()"
    )

    @property
    def latest_assessment(self) -> "Assessment | None":
        return self.assessments[0] if self.assessments else None


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True
    )
    summary: Mapped[str | None] = mapped_column(Text)
    total_years_experience: Mapped[float | None] = mapped_column(Numeric(4, 1, asdecimal=False))
    skills: Mapped[list] = mapped_column(JSONType, default=list)
    experience: Mapped[list] = mapped_column(JSONType, default=list)
    education: Mapped[list] = mapped_column(JSONType, default=list)
    certifications: Mapped[list] = mapped_column(JSONType, default=list)
    languages: Mapped[list] = mapped_column(JSONType, default=list)
    raw_response: Mapped[dict | None] = mapped_column(JSONType)
    model_name: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="profile")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False))
    must_have_met: Mapped[bool] = mapped_column(Boolean)
    criterion_scores: Mapped[list] = mapped_column(JSONType)
    strengths: Mapped[list] = mapped_column(JSONType, default=list)
    gaps: Mapped[list] = mapped_column(JSONType, default=list)
    interview_questions: Mapped[list] = mapped_column(JSONType, default=list)
    criteria_snapshot: Mapped[list] = mapped_column(JSONType)
    raw_response: Mapped[dict | None] = mapped_column(JSONType)
    model_name: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="assessments")


class RecruiterReview(Base):
    __tablename__ = "recruiter_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    reviewer: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor: Mapped[str] = mapped_column(Text, default="system")
    payload: Mapped[dict | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
