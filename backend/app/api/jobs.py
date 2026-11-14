"""Jobs and CV uploads."""
import hashlib
import uuid
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Application, Candidate, Job
from ..schemas import ApplicationSummary, JobCreate, JobOut, JobUpdate, UploadResult
from ..services.events import audit
from ..services.pdf import looks_like_pdf
from ..services.pipeline import process_application
from .common import get_or_404, summarise

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_out(job: Job) -> JobOut:
    counts = Counter(a.status for a in job.applications)
    out = JobOut.model_validate(job)
    out.application_count = len(job.applications)
    out.processing_count = counts["received"] + counts["processing"]
    out.analysed_count = len(job.applications) - out.processing_count - counts["failed"]
    return out


@router.post("", response_model=JobOut, status_code=201)
def create_job(body: JobCreate, db: Session = Depends(get_db)):
    job = Job(**body.model_dump(exclude={"criteria"}), criteria=[c.model_dump() for c in body.criteria])
    db.add(job)
    db.flush()
    audit(db, "job.created", "job", job.id, {"title": job.title}, actor="recruiter")
    db.commit()
    return _job_out(job)


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return [_job_out(j) for j in db.scalars(select(Job).order_by(Job.created_at.desc()))]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return _job_out(get_or_404(db, Job, job_id))


@router.patch("/{job_id}", response_model=JobOut)
def update_job(job_id: uuid.UUID, body: JobUpdate, db: Session = Depends(get_db)):
    """Changing criteria weights re-ranks instantly: scores are recomputed on read."""
    job = get_or_404(db, Job, job_id)
    changes = body.model_dump(exclude_unset=True)
    if "criteria" in changes:
        changes["criteria"] = [c.model_dump() for c in body.criteria]
    for field, value in changes.items():
        setattr(job, field, value)
    audit(db, "job.updated", "job", job.id, {"fields": sorted(changes)}, actor="recruiter")
    db.commit()
    return _job_out(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = get_or_404(db, Job, job_id)
    for app in job.applications:
        Path(app.cv_storage_path).unlink(missing_ok=True)
    db.delete(job)
    audit(db, "job.deleted", "job", job_id, actor="recruiter")
    db.commit()


@router.post("/{job_id}/applications", response_model=UploadResult, status_code=202)
async def upload_cvs(job_id: uuid.UUID, background: BackgroundTasks,
                     files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Accept one or many PDF CVs. Returns immediately (202); analysis runs in the background."""
    job = get_or_404(db, Job, job_id)
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    folder = Path(settings.upload_dir) / str(job.id)
    folder.mkdir(parents=True, exist_ok=True)

    batch_id = uuid.uuid4()
    known_hashes = set(db.scalars(select(Application.cv_sha256).where(Application.job_id == job.id)))
    accepted, rejected, new_apps = [], [], []

    for f in files:
        name = Path(f.filename or "cv.pdf").name
        data = await f.read(max_bytes + 1)
        if len(data) > max_bytes:
            rejected.append({"filename": name, "reason": f"larger than {settings.max_upload_mb} MB"})
            continue
        if not looks_like_pdf(data):
            rejected.append({"filename": name, "reason": "not a PDF file"})
            continue
        sha = hashlib.sha256(data).hexdigest()
        if sha in known_hashes:
            rejected.append({"filename": name, "reason": "duplicate — this CV was already uploaded for this job"})
            continue
        known_hashes.add(sha)

        app_id = uuid.uuid4()
        path = folder / f"{app_id}.pdf"
        path.write_bytes(data)
        candidate = Candidate(full_name=Path(name).stem.replace("_", " ").replace("-", " "))
        app = Application(id=app_id, job=job, candidate=candidate, cv_filename=name,
                          cv_storage_path=str(path), cv_sha256=sha, upload_batch_id=batch_id)
        db.add(app)
        audit(db, "application.received", "application", app_id, {"filename": name})
        new_apps.append(app)
        accepted.append({"application_id": str(app_id), "filename": name})

    db.commit()
    for app in new_apps:
        background.add_task(process_application, app.id)
    if not accepted and rejected:
        raise HTTPException(status_code=400, detail={"message": "No files accepted", "rejected": rejected})
    return UploadResult(batch_id=batch_id, accepted=accepted, rejected=rejected)


@router.get("/{job_id}/applications", response_model=list[ApplicationSummary])
def ranked_applications(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Candidates for a job, highest score first; unscored applications last."""
    job = get_or_404(db, Job, job_id)
    rows = [summarise(a, job) for a in job.applications]
    return sorted(rows, key=lambda r: (r.overall_score is None, -(r.overall_score or 0), r.created_at))
