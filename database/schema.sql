-- AI Recruitment Assistant — PostgreSQL schema (v1)
-- Loaded automatically by the postgres container on first start
-- (mounted into /docker-entrypoint-initdb.d). Alembic will take over in Stage 2.

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Jobs (vacancies) and their configurable assessment criteria
-- ---------------------------------------------------------------------------
CREATE TABLE jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title         TEXT        NOT NULL,
    department    TEXT,
    location      TEXT,
    description   TEXT        NOT NULL,
    -- [{"key","label","weight","must_have"}] — see docs/architecture.md §4
    criteria      JSONB       NOT NULL DEFAULT '[]'::jsonb,
    status        TEXT        NOT NULL DEFAULT 'open'
                  CHECK (status IN ('draft', 'open', 'closed')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Candidates (people) — one person may apply to many jobs
-- ---------------------------------------------------------------------------
CREATE TABLE candidates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name   TEXT,
    email       TEXT,
    phone       TEXT,
    location    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX candidates_email_uq ON candidates (lower(email)) WHERE email IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Applications — a candidate's CV submitted to a job; drives the pipeline
-- ---------------------------------------------------------------------------
CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'received'
                    CHECK (status IN ('received', 'processing', 'analysed', 'failed',
                                      'shortlisted', 'on_hold', 'not_progressing')),
    failure_reason  TEXT,
    cv_filename     TEXT NOT NULL,          -- original filename
    cv_storage_path TEXT NOT NULL,          -- path on the uploads volume
    cv_sha256       TEXT NOT NULL,          -- detect duplicate uploads
    cv_text         TEXT,                   -- PyMuPDF output
    upload_batch_id UUID,                   -- groups a multi-file upload (n8n batch report)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, cv_sha256)
);
CREATE INDEX applications_job_status_idx ON applications (job_id, status);

-- ---------------------------------------------------------------------------
-- Candidate profile — AI structured extraction (Gemini call #1)
-- ---------------------------------------------------------------------------
CREATE TABLE candidate_profiles (
    application_id          UUID PRIMARY KEY REFERENCES applications(id) ON DELETE CASCADE,
    summary                 TEXT,
    total_years_experience  NUMERIC(4,1),
    skills                  JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{"name","category","years"}]
    experience              JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{"title","company","start","end","highlights"}]
    education               JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{"qualification","institution","year"}]
    certifications          JSONB NOT NULL DEFAULT '[]'::jsonb,
    languages               JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_response            JSONB,
    model_name              TEXT NOT NULL,
    prompt_version          TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Assessments — AI evaluation against job criteria (Gemini call #2)
-- Multiple rows per application keep history when re-analysed.
-- ---------------------------------------------------------------------------
CREATE TABLE assessments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id      UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    overall_score       NUMERIC(5,2) NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    must_have_met       BOOLEAN NOT NULL,
    -- [{"key","score","evidence":[...],"reasoning"}] — score 0–5 per criterion
    criterion_scores    JSONB NOT NULL,
    strengths           JSONB NOT NULL DEFAULT '[]'::jsonb,
    gaps                JSONB NOT NULL DEFAULT '[]'::jsonb,
    interview_questions JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{"question","purpose","criterion_key"}]
    criteria_snapshot   JSONB NOT NULL,     -- job criteria as they were when scored
    raw_response        JSONB,
    model_name          TEXT NOT NULL,
    prompt_version      TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX assessments_application_idx ON assessments (application_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Recruiter reviews — the human decisions (the only thing that changes outcome)
-- ---------------------------------------------------------------------------
CREATE TABLE recruiter_reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    reviewer        TEXT NOT NULL,
    decision        TEXT NOT NULL CHECK (decision IN ('shortlisted', 'on_hold', 'not_progressing')),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Audit log — append-only trail of significant events
-- ---------------------------------------------------------------------------
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    event_type  TEXT NOT NULL,        -- e.g. application.received, application.analysed, review.created
    entity_type TEXT NOT NULL,
    entity_id   UUID,
    actor       TEXT NOT NULL DEFAULT 'system',
    payload     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_entity_idx ON audit_log (entity_type, entity_id);
