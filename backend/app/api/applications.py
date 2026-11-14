"""Application detail, re-analysis, recruiter reviews, CV download."""
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Application, RecruiterReview
from ..schemas import ApplicationDetail, AssessmentOut, CandidateOut, ProfileOut, ReviewIn, ReviewOut
from ..services.events import audit, emit
from ..services.pipeline import process_application
from .common import get_or_404, live_score

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("/{app_id}", response_model=ApplicationDetail)
def get_application(app_id: uuid.UUID, db: Session = Depends(get_db)):
    app = get_or_404(db, Application, app_id)
    a, score = app.latest_assessment, live_score(app, app.job)
    return ApplicationDetail(
        id=app.id,
        job={"id": str(app.job.id), "title": app.job.title},
        candidate=CandidateOut.model_validate(app.candidate),
        status=app.status,
        failure_reason=app.failure_reason,
        cv_filename=app.cv_filename,
        created_at=app.created_at,
        profile=ProfileOut.model_validate(app.profile) if app.profile else None,
        assessment=AssessmentOut(
            overall_score=score.overall,
            must_have_met=score.must_have_met,
            score_at_analysis=a.overall_score,
            criteria=score.criteria,
            strengths=a.strengths,
            gaps=a.gaps,
            interview_questions=a.interview_questions,
            model_name=a.model_name,
            prompt_version=a.prompt_version,
            created_at=a.created_at,
        ) if a else None,
        reviews=[ReviewOut.model_validate(r) for r in app.reviews],
    )


@router.post("/{app_id}/reanalyse", status_code=202)
def reanalyse(app_id: uuid.UUID, background: BackgroundTasks, db: Session = Depends(get_db)):
    app = get_or_404(db, Application, app_id)
    if app.status == "processing":
        raise HTTPException(status_code=409, detail="Already processing")
    app.status = "received"
    audit(db, "application.reanalyse_requested", "application", app.id, actor="recruiter")
    db.commit()
    background.add_task(process_application, app.id)
    return {"status": "queued"}


@router.post("/{app_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(app_id: uuid.UUID, body: ReviewIn, db: Session = Depends(get_db)):
    """The human decision. This — not the AI score — is what moves a candidate forward."""
    app = get_or_404(db, Application, app_id)
    if app.status in ("received", "processing"):
        raise HTTPException(status_code=409, detail="Wait for the analysis to finish before reviewing")
    review = RecruiterReview(application_id=app.id, **body.model_dump())
    db.add(review)
    app.status = body.decision
    audit(db, "review.created", "application", app.id, body.model_dump(), actor=body.reviewer)
    db.commit()
    emit("review.created", {"application_id": str(app.id), "job_title": app.job.title,
                            "candidate_name": app.candidate.full_name, **body.model_dump()})
    return review


@router.get("/{app_id}/cv")
def download_cv(app_id: uuid.UUID, db: Session = Depends(get_db)):
    app = get_or_404(db, Application, app_id)
    if not Path(app.cv_storage_path).exists():
        raise HTTPException(status_code=404, detail="CV file missing from storage")
    return FileResponse(app.cv_storage_path, media_type="application/pdf", filename=app.cv_filename,
                        content_disposition_type="inline")


@router.delete("/{app_id}", status_code=204)
def delete_application(app_id: uuid.UUID, db: Session = Depends(get_db)):
    app = get_or_404(db, Application, app_id)
    Path(app.cv_storage_path).unlink(missing_ok=True)
    db.delete(app)
    audit(db, "application.deleted", "application", app_id, actor="recruiter")
    db.commit()
