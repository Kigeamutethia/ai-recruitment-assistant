# AI Recruitment Assistant — Architecture

> Stage 1 deliverable. This document is the single source of truth for *how* the system is put
> together and *why*. Read it before touching code; update it when a decision changes.

## 1. Purpose and principles

The system helps a recruiter process a stack of CVs for a vacancy: it extracts structured
information, compares each candidate's evidence against the job's requirements, produces an
explainable assessment and suggests interview questions.

Guiding principles (these are also good interview talking points):

| Principle | What it means in practice |
|---|---|
| **Human in the loop** | AI *assists*. It never rejects anyone. Every status change after analysis is made by a recruiter and recorded. |
| **Evidence over vibes** | Every score must be backed by a quote/snippet from the CV. No evidence → no credit. |
| **Deterministic ranking** | The LLM scores each criterion; **Python** combines them with recruiter-configured weights. Ranking is reproducible and explainable. |
| **Fairness by design** | Protected characteristics (age, gender, ethnicity, photo, marital status, nationality) are never extracted or scored. Names are shown in the UI but not sent into the scoring prompt. |
| **Traceability** | Store model name, prompt version and raw AI output alongside every result. |
| **Provider-agnostic AI** | A small `LLMProvider` interface; Gemini is the first implementation. |

## 2. System context

```
                ┌──────────────────────────── Docker Compose ───────────────────────────┐
                │                                                                       │
 Recruiter ───► │  React dashboard ──HTTP/JSON──► FastAPI backend ──SQL──► PostgreSQL   │
  (browser)     │   (Vite, :5173)                  (:8000)                  (:5432)     │
                │                                    │   │                              │
                │                       PyMuPDF ◄────┘   └────► Gemini API (Google)     │
                │                      (PDF → text)               (structured JSON)     │
                │                                    │                                  │
                │                                    └── webhook ──► n8n (:5678)        │
                │                                                     │ email / Slack / │
                │                                                     │ daily report    │
                └─────────────────────────────────────────────────────┴─────────────────┘
```

| Component | Tech | Responsibility |
|---|---|---|
| Frontend | React + Vite + TypeScript | Job management, CV upload, ranked candidate list, assessment detail, recruiter review. |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2 | REST API, file handling, orchestration of the analysis pipeline, scoring. |
| Document processing | PyMuPDF (`pymupdf`) | Extract text from PDFs; detect scanned/empty PDFs. |
| AI engine | Google Gemini via `google-genai` SDK | Structured extraction, criterion assessment, interview questions — using JSON-schema-constrained output. |
| Database | PostgreSQL 17 | Jobs, candidates, applications, extracted profiles, assessments, reviews, audit log. |
| Automation | n8n | Reacts to backend events (webhooks): notifications, daily summary reports. Not in the critical path. |
| Deployment | Docker Compose | One command brings up the whole stack locally. |

## 3. End-to-end workflow

1. **Recruiter creates a job** — title, description, and a list of *criteria*
   (e.g. "Python ≥ 3 yrs", "FastAPI", "Degree in CS or equivalent"), each with a weight and a
   `must_have` flag.
2. **CVs are uploaded** (one or many PDFs) against that job. The backend stores the file,
   creates `candidate` + `application` rows with status `received`, and returns immediately.
3. **Background analysis** (FastAPI `BackgroundTasks` to start; a queue later if needed):
   1. `extract_text` — PyMuPDF → plain text. Empty text ⇒ status `failed` with reason `scanned_pdf`.
   2. `extract_profile` — Gemini call #1: CV text → `CandidateProfile` JSON (skills, roles,
      education, certifications, years of experience). Contact details are parsed here too.
   3. `assess` — Gemini call #2: anonymised profile + CV text + job criteria →
      per-criterion `{score 0–5, evidence[], reasoning}`, strengths, gaps, interview questions.
   4. `score` — Python: weighted average of criterion scores, must-have flags, final 0–100 score.
   5. Status → `analysed`; backend fires webhook `application.analysed` to n8n.
4. **n8n** sends notifications / compiles reports.
5. **Recruiter reviews** the ranked list in the dashboard, reads the evidence, and records a
   decision (`shortlisted`, `on_hold`, `not_progressing`) with notes. That decision is the
   only thing that moves a candidate forward or not.

### Application status machine

```
received ──► processing ──► analysed ──► (recruiter) shortlisted | on_hold | not_progressing
                  │
                  └──► failed  (can be retried → processing)
```

## 4. Scoring model

Each job has criteria:

```json
[
  {"key": "python",  "label": "Python (3+ years, production)", "weight": 3, "must_have": true},
  {"key": "fastapi", "label": "FastAPI or similar REST framework", "weight": 2, "must_have": false},
  {"key": "sql",     "label": "Relational databases / SQL",     "weight": 2, "must_have": false},
  {"key": "cloud",   "label": "Cloud deployment (AWS/GCP/Azure)", "weight": 1, "must_have": false}
]
```

Gemini returns a score `0–5` per criterion **with evidence quotes**. Python then computes:

```
overall = 100 × Σ(weight_i × score_i) / Σ(weight_i × 5)
must_have_met = all(score_i ≥ 3 for must-have criteria)
```

`must_have_met = false` is shown as a **flag** for the recruiter, never an automatic rejection.
Because the formula lives in code, re-weighting criteria re-ranks candidates instantly
without another AI call.

## 5. Data model

See [`database/schema.sql`](../database/schema.sql) for the DDL. Overview:

```
jobs 1──* applications *──1 candidates
             │
             ├──1 candidate_profiles   (AI extraction output)
             ├──* assessments          (AI assessment; latest one is current — keeps history on re-run)
             └──* recruiter_reviews    (human decisions)

audit_log  (append-only record of significant events)
```

Design notes:
- `candidates` is separate from `applications` so one person can apply to several jobs.
  Deduplicated by email when one is found.
- AI outputs are stored as `JSONB` *plus* a few promoted columns (`overall_score`,
  `total_years_experience`) that we sort/filter on.
- `model_name` and `prompt_version` are stored with every AI result.

## 6. API surface (planned, Stage 2–3)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/jobs` | Create job with criteria |
| `GET` | `/api/jobs` / `/api/jobs/{id}` | List / get jobs |
| `PATCH` | `/api/jobs/{id}` | Update job, criteria weights |
| `POST` | `/api/jobs/{id}/applications` | Upload one or more CVs (multipart) |
| `GET` | `/api/jobs/{id}/applications?sort=score` | Ranked candidate list |
| `GET` | `/api/applications/{id}` | Full detail: profile, assessment, evidence, questions |
| `POST` | `/api/applications/{id}/reanalyse` | Re-run AI pipeline |
| `POST` | `/api/applications/{id}/reviews` | Recruiter decision + notes |
| `GET` | `/api/applications/{id}/cv` | Download original PDF |
| `GET` | `/api/health` | Liveness for Docker |

## 7. AI integration design (Stage 3)

```python
class LLMProvider(Protocol):
    model_name: str
    def extract_profile(self, cv_text: str) -> CandidateExtraction: ...
    def assess(self, *, title, description, criteria, extraction, cv_text) -> CandidateAssessment: ...

class GeminiProvider: ...   # google-genai, response_schema=<Pydantic model>   (backend/app/ai/gemini.py)
class FakeProvider: ...     # keyword heuristics, no network: tests + offline demo (backend/app/ai/fake.py)
```

- `AI_PROVIDER=auto` (default) uses Gemini when `GEMINI_API_KEY` is set, otherwise the fake provider.
- Prompts live in `backend/app/ai/prompts.py` as versioned templates (`PROMPT_VERSION`).
- Before the assessment call, name/email/phone are redacted from both the CV text and the profile JSON.
- Gemini's JSON-schema output mode is used so responses validate directly into Pydantic models.
- Model name comes from config (`GEMINI_MODEL`) so it can be changed without code changes.
- Retries with backoff on transient errors; failures set the application to `failed` with a reason.

## 8. n8n automation (Stage 4)

Backend → n8n via webhooks (`N8N_WEBHOOK_URL`). Initial workflows:

1. **Application analysed** → notify recruiter (email/Slack) with score + link.
2. **Batch complete** → summary when all CVs for an upload batch are analysed.
3. **Daily digest** (cron) → n8n calls `GET /api/jobs/{id}/applications` and emails a report.

n8n is deliberately *outside* the critical path: if it's down, analysis still works.

## 9. Security and privacy

- Secrets only in `.env` (git-ignored); `.env.example` documents them.
- Uploaded CVs stored on a Docker volume, not in the repo; `sample_data/` contains only fictional CVs.
- Upload validation: PDF MIME/magic bytes, size limit (default 10 MB).
- CV text is sent to Google's API — documented in the README; demo uses fictional CVs only.
- Simple API-key/JWT auth for recruiter endpoints is added in Stage 5 (portfolio scope).

## 10. Repository layout

```
├── backend/          FastAPI app (app/api, app/models, app/services, app/ai), Dockerfile
├── frontend/         React + Vite dashboard
├── automation/       n8n workflow exports (JSON)
├── database/         schema.sql (+ Alembic migrations later)
├── docs/             architecture, decisions, screenshots
├── tests/            pytest suites (unit + API)
├── sample_data/      fictional CVs and job descriptions for demos
├── docker-compose.yml
└── .env.example
```

## 11. Decision log

| # | Decision | Why |
|---|---|---|
| D1 | Build from scratch | Portfolio goal: every component explainable in interviews. |
| D2 | Gemini, behind an interface | User choice; interface keeps it swappable and testable. |
| D3 | LLM scores criteria, code computes ranking | Explainable, reproducible, cheap to re-weight. |
| D4 | Two AI calls (extract, then assess) | Smaller focused prompts; profile reusable across jobs. |
| D5 | BackgroundTasks before a job queue | Simplest thing that works; upgrade path to Celery/RQ is clear. |
| D6 | Python 3.12 in Docker | Host has 3.14; some native wheels may lag. Container pins a stable runtime. |
| D7 | n8n via webhooks, non-critical | Automation failures must not break core processing. |
| D8 | Offline `FakeProvider` | Tests and demos run without an API key or network; CI is free and deterministic. |
| D9 | Scores recomputed on read | The ranked list applies the job's *current* weights to stored criterion scores, so re-weighting is instant. `score_at_analysis` is kept for audit. |
| D10 | Ports configurable via `.env` | Lets the stack coexist with other local services (e.g. another n8n on 5678). |
