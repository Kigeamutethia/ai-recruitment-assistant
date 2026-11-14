"""Structured-output schemas the LLM must return.

These Pydantic models are passed to Gemini as `response_schema`, so the model is constrained
to emit JSON of exactly this shape, and the reply validates straight into Python objects.
(No default values here: Gemini's schema mode rejects them.)
"""
from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    category: str  # language | framework | database | cloud | tool | methodology | soft_skill | domain | other
    years: float | None


class Experience(BaseModel):
    title: str
    company: str
    start: str
    end: str
    highlights: list[str]


class Education(BaseModel):
    qualification: str
    institution: str
    year: str


class CandidateExtraction(BaseModel):
    """AI call #1 output: what the CV says, structured."""

    full_name: str
    email: str
    phone: str
    location: str
    summary: str
    total_years_experience: float | None
    skills: list[Skill]
    experience: list[Experience]
    education: list[Education]
    certifications: list[str]
    languages: list[str]


class CriterionAssessment(BaseModel):
    key: str
    score: int = Field(ge=0, le=5)
    evidence: list[str] = Field(max_length=3)  # short verbatim quotes from the CV
    reasoning: str


class InterviewQuestion(BaseModel):
    question: str
    purpose: str
    criterion_key: str


class CandidateAssessment(BaseModel):
    """AI call #2 output: evidence-based assessment against the job criteria.

    max_length on lists becomes `maxItems` in the JSON schema, so the model cannot ramble.
    """

    criteria: list[CriterionAssessment] = Field(max_length=20)
    strengths: list[str] = Field(max_length=5)
    gaps: list[str] = Field(max_length=5)
    interview_questions: list[InterviewQuestion] = Field(max_length=8)
