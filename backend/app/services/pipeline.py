"""The CV analysis pipeline: PDF -> text -> AI extraction -> AI assessment -> score -> store -> notify.

Runs as a FastAPI background task after the upload request has returned, so it opens its own
database session.
"""
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from .. import db as db_module
from ..ai.prompts import PROMPT_VERSION
from ..ai.provider import LLMProvider, get_provider
from ..ai.schemas import CandidateExtraction
from ..config import get_settings
from ..models import Application, Assessment, Candidate, CandidateProfile
from .events import audit, emit
from .pdf import extract_text
from .scoring import compute_score

log = logging.getLogger(__name__)
TERMINAL = {"analysed", "failed", "shortlisted", "on_hold", "not_progressing"}


def process_application(application_id: uuid.UUID, *, session_factory: sessionmaker | None = None,
                        provider: LLMProvider | None = None) -> None:
    factory = session_factory or db_module.SessionLocal
    with factory() as db:
        app = db.get(Application, application_id)
        if app is None:
            return
        app.status, app.failure_reason = "processing", None
        db.commit()

        try:
            provider = provider or get_provider()
            _run(db, app, provider)
            db.commit()
        except Exception as e:  # any failure -> visible 'failed' status, never a silent loss
            log.exception("Analysis failed for application %s", application_id)
            db.rollback()
            app = db.get(Application, application_id)
            app.status, app.failure_reason = "failed", str(e)[:500]
            audit(db, "application.failed", "application", app.id, {"reason": app.failure_reason})
            db.commit()
            emit("application.failed", _event_data(app))
        else:
            emit("application.analysed", _event_data(app))
        _maybe_emit_batch_completed(db, app)


def _run(db: Session, app: Application, provider: LLMProvider) -> None:
    # 1. Text extraction (cached on the row, so re-analysis skips it)
    if not app.cv_text:
        app.cv_text = extract_text(app.cv_storage_path)

    # 2. AI call #1 — structured extraction
    extraction = provider.extract_profile(app.cv_text)
    _update_candidate(db, app, extraction)
    if app.profile is None:
        app.profile = CandidateProfile(application_id=app.id, model_name="", prompt_version="")
    p = app.profile
    p.summary = extraction.summary
    p.total_years_experience = extraction.total_years_experience
    p.skills = [s.model_dump() for s in extraction.skills]
    p.experience = [e.model_dump() for e in extraction.experience]
    p.education = [e.model_dump() for e in extraction.education]
    p.certifications = extraction.certifications
    p.languages = extraction.languages
    p.raw_response = extraction.model_dump()
    p.model_name, p.prompt_version = provider.model_name, PROMPT_VERSION

    # 3. AI call #2 — assessment against the job's criteria (anonymised input)
    job = app.job
    result = provider.assess(title=job.title, description=job.description, criteria=job.criteria,
                             extraction=extraction, cv_text=app.cv_text)
    criterion_scores = [c.model_dump() for c in result.criteria]

    # 4. Deterministic score
    score = compute_score(job.criteria, criterion_scores)
    db.add(Assessment(
        application_id=app.id,
        overall_score=score.overall,
        must_have_met=score.must_have_met,
        criterion_scores=criterion_scores,
        strengths=result.strengths,
        gaps=result.gaps,
        interview_questions=[q.model_dump() for q in result.interview_questions],
        criteria_snapshot=job.criteria,
        raw_response=result.model_dump(),
        model_name=provider.model_name,
        prompt_version=PROMPT_VERSION,
    ))
    app.status = "analysed"
    audit(db, "application.analysed", "application", app.id,
          {"overall_score": score.overall, "must_have_met": score.must_have_met, "model": provider.model_name})
    db.flush()
    db.refresh(app)  # load the new assessment into app.assessments for the event payload


def _update_candidate(db: Session, app: Application, ex: CandidateExtraction) -> None:
    """Fill in contact details; if the email belongs to an existing candidate, link to them instead."""
    cand = app.candidate
    email = ex.email.strip().lower() or None
    if email:
        existing = db.scalar(select(Candidate).where(func.lower(Candidate.email) == email,
                                                     Candidate.id != cand.id))
        if existing:
            app.candidate = existing
            if len(cand.applications) <= 1:
                db.delete(cand)
            cand = existing
    cand.full_name = ex.full_name or cand.full_name
    cand.email = email or cand.email
    cand.phone = ex.phone or cand.phone
    cand.location = ex.location or cand.location


def _event_data(app: Application) -> dict:
    a = app.latest_assessment
    return {
        "application_id": str(app.id),
        "job_id": str(app.job_id),
        "job_title": app.job.title,
        "candidate_name": app.candidate.full_name,
        "status": app.status,
        "failure_reason": app.failure_reason,
        "overall_score": a.overall_score if a else None,
        "must_have_met": a.must_have_met if a else None,
        "url": f"{get_settings().public_app_url}/applications/{app.id}",
    }


def _maybe_emit_batch_completed(db: Session, app: Application) -> None:
    if app.upload_batch_id is None:
        return
    batch = db.scalars(select(Application).where(Application.upload_batch_id == app.upload_batch_id)).all()
    if not all(a.status in TERMINAL for a in batch):
        return
    analysed = sorted((a for a in batch if a.latest_assessment), key=lambda a: -a.latest_assessment.overall_score)
    emit("batch.completed", {
        "batch_id": str(app.upload_batch_id),
        "job_id": str(app.job_id),
        "job_title": app.job.title,
        "total": len(batch),
        "analysed": len(analysed),
        "failed": sum(a.status == "failed" for a in batch),
        "top_candidates": [
            {"name": a.candidate.full_name, "score": a.latest_assessment.overall_score} for a in analysed[:3]
        ],
        "url": f"{get_settings().public_app_url}/jobs/{app.job_id}",
    })
