"""Shared helpers for the API layer."""
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Application, Job
from ..schemas import ApplicationSummary
from ..services.scoring import compute_score


def get_or_404(db: Session, model, id_: uuid.UUID):
    obj = db.get(model, id_)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


def live_score(app: Application, job: Job):
    """Score the latest assessment against the job's *current* criteria/weights."""
    a = app.latest_assessment
    return compute_score(job.criteria, a.criterion_scores) if a else None


def summarise(app: Application, job: Job) -> ApplicationSummary:
    score = live_score(app, job)
    skills = app.profile.skills if app.profile else []
    return ApplicationSummary(
        id=app.id,
        job_id=app.job_id,
        candidate_name=app.candidate.full_name,
        candidate_email=app.candidate.email,
        status=app.status,
        failure_reason=app.failure_reason,
        cv_filename=app.cv_filename,
        created_at=app.created_at,
        overall_score=score.overall if score else None,
        must_have_met=score.must_have_met if score else None,
        total_years_experience=app.profile.total_years_experience if app.profile else None,
        top_skills=[s["name"] for s in skills[:6]],
    )
