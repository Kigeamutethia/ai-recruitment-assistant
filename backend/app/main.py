"""FastAPI application entrypoint.  Run: uvicorn app.main:app --reload"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .ai.provider import provider_name
from .api import applications, jobs, reports
from .config import get_settings
from .db import engine
from .models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # In Postgres the tables come from database/schema.sql; create_all only fills gaps
    # (and builds the schema for SQLite in tests).
    Base.metadata.create_all(engine)
    Path(get_settings().upload_dir).mkdir(parents=True, exist_ok=True)
    # Background tasks die with the process: anything mid-analysis at startup was interrupted.
    with engine.begin() as conn:
        conn.execute(text("UPDATE applications SET status = 'failed', "
                          "failure_reason = 'Interrupted by a server restart, please re-analyse' "
                          "WHERE status IN ('received', 'processing')"))
    yield


app = FastAPI(
    title="AI Recruitment Assistant",
    version="0.1.0",
    description="AI-assisted CV analysis with evidence-based, recruiter-controlled assessments.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(reports.router)


@app.get("/api/health", tags=["meta"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "ai_provider": provider_name()}
