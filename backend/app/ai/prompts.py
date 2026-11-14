"""Versioned prompt templates.

Bump PROMPT_VERSION whenever a prompt changes meaningfully — it is stored with every AI result,
so you can always tell which prompt produced which assessment.
"""
import json
import re

from .schemas import CandidateExtraction

PROMPT_VERSION = "v1"
MAX_CV_CHARS = 30_000

EXTRACT_TEMPLATE = """You extract structured information from CVs for a recruitment team.

Rules:
- Extract only what is written in the CV. Never infer or invent facts.
- Do NOT extract or mention age, date of birth, gender, ethnicity, nationality, religion,
  marital status, health, or photos.
- Use an empty string for unknown text fields, null for unknown numbers, and empty lists when nothing applies.
- total_years_experience: total professional work experience in years (count overlapping roles once), one decimal.
- skills[].category is one of: language, framework, database, cloud, tool, methodology, soft_skill, domain, other.
- skills[].years: only if the CV states or clearly implies it, else null.
- Keep dates as written (e.g. "2021-03", "2019", "Present").
- summary: 2-3 neutral sentences describing the candidate's professional background.

CV TEXT:
<<<
{cv_text}
>>>"""

ASSESS_TEMPLATE = """You assist a recruiter by assessing a candidate against job criteria.
You do not make hiring decisions; a human recruiter reviews your output.

Score each criterion from 0 to 5:
  0 = no evidence, 1 = minimal or indirect, 2 = some but below requirement,
  3 = meets the requirement, 4 = strong, 5 = exceptional / clearly exceeds.

Rules:
- Base every score ONLY on evidence in the candidate material below.
- In `evidence`, quote short exact snippets from the CV (max 25 words each). No evidence -> score 0, empty evidence.
- Never consider protected characteristics (age, gender, ethnicity, nationality, religion, disability,
  marital status). Personal details have been redacted.
- Do not penalise career gaps, non-traditional education routes or CV formatting.
- Return exactly one entry per criterion, using the criterion's `key`.
- strengths and gaps: 2-5 concise points each, specific to this job.
- interview_questions: 5-8 questions that probe specific claims in the CV and gaps against the criteria.
  criterion_key is the related criterion key, or "general".

JOB TITLE: {title}

JOB DESCRIPTION:
{description}

CRITERIA (JSON):
{criteria_json}

CANDIDATE PROFILE (JSON, redacted):
{profile_json}

CV TEXT (redacted):
<<<
{cv_text}
>>>"""


def build_extract_prompt(cv_text: str) -> str:
    return EXTRACT_TEMPLATE.format(cv_text=cv_text[:MAX_CV_CHARS])


def redact(text: str, extraction: CandidateExtraction) -> str:
    """Remove direct identifiers before the assessment call, so the score can't depend on them."""
    for value in (extraction.email, extraction.phone):
        if value:
            text = text.replace(value, "[REDACTED]")
    for part in extraction.full_name.split():
        if len(part) > 1:
            text = re.sub(rf"\b{re.escape(part)}\b", "[REDACTED]", text, flags=re.IGNORECASE)
    return text


def anonymised_profile(extraction: CandidateExtraction) -> dict:
    return extraction.model_dump(exclude={"full_name", "email", "phone", "location"})


def build_assess_prompt(title: str, description: str, criteria: list[dict],
                        extraction: CandidateExtraction, cv_text: str) -> str:
    criteria_for_llm = [
        {"key": c["key"], "label": c["label"], "must_have": c.get("must_have", False)} for c in criteria
    ]
    return ASSESS_TEMPLATE.format(
        title=title,
        description=description,
        criteria_json=json.dumps(criteria_for_llm, indent=2),
        # Free-text fields (summary, titles) can still mention the name/email, so redact those too.
        profile_json=redact(json.dumps(anonymised_profile(extraction), indent=2), extraction),
        cv_text=redact(cv_text, extraction)[:MAX_CV_CHARS],
    )
