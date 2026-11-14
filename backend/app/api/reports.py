"""Reporting endpoints — consumed by the n8n daily digest workflow."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Job
from .common import summarise

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    jobs = []
    for job in db.scalars(select(Job).where(Job.status == "open").order_by(Job.created_at)):
        rows = [summarise(a, job) for a in job.applications]
        scored = sorted((r for r in rows if r.overall_score is not None), key=lambda r: -r.overall_score)
        jobs.append({
            "job_id": str(job.id),
            "title": job.title,
            "total_applications": len(rows),
            "new_last_24h": sum(1 for a in job.applications if _aware(a.created_at) >= since),
            "by_status": dict(Counter(r.status for r in rows)),
            "awaiting_review": sum(r.status == "analysed" for r in rows),
            "top_candidates": [
                {"name": r.candidate_name, "score": r.overall_score, "must_have_met": r.must_have_met,
                 "status": r.status} for r in scored[:3]
            ],
        })
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "open_jobs": jobs}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite returns naive datetimes
