# AI Recruitment Assistant

An AI-assisted recruitment platform. It reads PDF CVs, extracts structured candidate
information with Google Gemini, assesses each candidate against recruiter-defined, weighted
criteria with **evidence quotes for every score**, ranks candidates in a way you can explain,
and suggests tailored interview questions.

**Recruiters stay in control:** the AI never rejects anyone. Its scores are advisory, and every
decision is made and recorded by a person.

## Features

- **Bulk PDF upload** with duplicate detection, size and type validation, and processing in the background
- **Structured extraction**: skills, experience, education, certifications and years of experience
- **Evidence-based assessment**: a 0–5 score per criterion, backed by quotes from the CV
- **Deterministic, re-weightable ranking**: change a weight and every candidate is re-ranked instantly, with no new AI calls
- **Must-have flags** that highlight gaps for the recruiter instead of rejecting anyone automatically
- **Tailored interview questions** that probe the claims and gaps in each CV
- **Recruiter dashboard** for reviewing candidates and recording decisions, with history
- **Audit trail**: every AI result stores the model name, prompt version and raw output
- **n8n automation**: per-candidate and per-batch notifications, plus a weekday digest email
- **Offline mode**: a heuristic provider runs the full pipeline without an API key (also used in tests and CI)

## Architecture

```
React dashboard ──► FastAPI ──► PostgreSQL
   (nginx)            │  ├──► PyMuPDF (PDF → text)
                      │  └──► Gemini (structured JSON output)
                      └── webhooks ──► n8n ──► email / digest
```

The pipeline for each CV is: extract text → **AI call 1**: structured profile → redact personal
details → **AI call 2**: assess against the criteria → **Python** combines the scores using the
recruiter's weights → store → notify.

Full design and decision log: [docs/architecture.md](docs/architecture.md)

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Router |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2 |
| AI | Google Gemini via `google-genai` (JSON-schema structured output), behind a provider interface |
| Documents | PyMuPDF |
| Database | PostgreSQL 17 |
| Automation | n8n |
| Delivery | Docker Compose, GitHub Actions CI |

## Getting started

Prerequisites: Docker (Docker Desktop, or Docker Engine in WSL2).

```bash
cp .env.example .env          # set POSTGRES_PASSWORD; optionally add GEMINI_API_KEY
docker compose up -d --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| n8n | http://localhost:5678 (or `N8N_PORT`) |

Load the demo data (one vacancy and four fictional CVs):

```bash
python sample_data/generate_cvs.py   # needs: pip install pymupdf httpx
python sample_data/seed.py
```

Import the automation workflows (see [automation/README.md](automation/README.md)):

```bash
docker compose exec n8n n8n import:workflow --separate --input=/workflows
docker compose exec n8n n8n publish:workflow --id=RecruitEvents001
docker compose exec n8n n8n publish:workflow --id=RecruitDigest001
docker compose restart n8n
```

### Using Gemini

Get a key at https://aistudio.google.com/apikey, set `GEMINI_API_KEY` in `.env`, then run
`docker compose up -d backend`. The header in the dashboard shows which AI provider is active.
`GEMINI_MODEL` selects the model.

## Local development

```bash
# Backend (Python 3.12)
python -m venv .venv && .venv/Scripts/activate      # Windows; use .venv/bin/activate on Linux/macOS
pip install -r backend/requirements-dev.txt
pytest -q                                            # SQLite + offline AI provider
cd backend && uvicorn app.main:app --reload          # uses DATABASE_URL from .env

# Frontend
cd frontend && npm install && npm run dev            # http://localhost:5173, proxies /api to :8000
```

## Project structure

```
backend/app/
  ai/          provider interface, Gemini + offline providers, prompts, output schemas
  api/         FastAPI routers: jobs, applications, reports
  services/    pdf extraction, analysis pipeline, scoring, audit/events
  models.py    SQLAlchemy ORM      schemas.py  API models
frontend/src/  pages (vacancies, ranked candidates, assessment detail), components
automation/    n8n workflow exports
database/      schema.sql
sample_data/   fictional job and CVs, generator, and seed script
tests/         pytest suite (scoring, redaction, end-to-end API)
```

## Responsible AI

- **Advisory only.** Status changes after analysis are made by recruiters and logged with their name and notes.
- **Fairness.** Protected characteristics are neither extracted nor scored. Name, email and phone are redacted before the scoring call, and a test enforces this.
- **Explainability.** Every criterion score comes with quoted evidence and reasoning. The final score is a transparent weighted formula.
- **Traceability.** The model, prompt version, raw output and the criteria in effect at analysis time are all stored.
- **Data protection.** CV text is sent to Google's Gemini API when it is enabled. Demos use fictional CVs only. Uploaded CVs live in a Docker volume and are never committed to git.

## Roadmap

- [x] Architecture, schema and infrastructure
- [x] Backend API, PDF extraction and persistence
- [x] Gemini integration: extraction, assessment, scoring and interview questions
- [x] n8n notifications and daily digest
- [x] Recruiter dashboard
- [x] Tests, Docker and CI
- [ ] Authentication for recruiter accounts
- [ ] OCR for scanned PDFs
- [ ] Alembic migrations
- [ ] Job queue (RQ/Celery) for large batches
