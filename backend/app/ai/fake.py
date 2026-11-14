"""Offline, deterministic provider — keyword heuristics, no network.

Used by the test suite and as a fallback demo mode when no GEMINI_API_KEY is configured.
It is intentionally simple; it exists so the whole pipeline can run end-to-end without an API.
"""
import re

from .schemas import (
    CandidateAssessment,
    CandidateExtraction,
    CriterionAssessment,
    Education,
    Experience,
    InterviewQuestion,
    Skill,
)

KNOWN_SKILLS = {
    "python": "language", "java": "language", "javascript": "language", "typescript": "language",
    "c#": "language", "go": "language", "sql": "language", "fastapi": "framework",
    "django": "framework", "flask": "framework", "react": "framework", "node.js": "framework",
    "postgresql": "database", "mysql": "database", "mongodb": "database", "redis": "database",
    "aws": "cloud", "azure": "cloud", "gcp": "cloud", "docker": "tool", "kubernetes": "tool",
    "git": "tool", "terraform": "tool", "agile": "methodology", "scrum": "methodology",
    "machine learning": "domain", "leadership": "soft_skill", "communication": "soft_skill",
}
STOPWORDS = {"and", "or", "the", "with", "for", "of", "in", "a", "an", "to", "years", "year",
             "experience", "similar", "equivalent", "degree", "production", "plus", "least"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d\s()-]{7,}\d")
RANGE_RE = re.compile(r"\b((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2}|present|current)\b", re.IGNORECASE)
CURRENT_YEAR = 2026


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


class FakeProvider:
    model_name = "fake-heuristic"

    def extract_profile(self, cv_text: str) -> CandidateExtraction:
        lines = _lines(cv_text)
        lower = cv_text.lower()
        email = EMAIL_RE.search(cv_text)
        phone = PHONE_RE.search(cv_text)

        years = 0
        for start, end in RANGE_RE.findall(cv_text):
            end_year = CURRENT_YEAR if not end.isdigit() else int(end)
            years += max(0, end_year - int(start))

        skills = [
            Skill(name=name, category=cat, years=None)
            for name, cat in KNOWN_SKILLS.items()
            if re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", lower)
        ]
        experience = [
            Experience(title=ln, company="", start="", end="", highlights=[])
            for ln in lines if RANGE_RE.search(ln)
        ][:6]
        education = [
            Education(qualification=ln, institution="", year="")
            for ln in lines if re.search(r"\b(bsc|msc|ba|ma|phd|degree|diploma|bachelor|master)\b", ln, re.I)
        ][:3]

        return CandidateExtraction(
            full_name=lines[0] if lines else "",
            email=email.group(0) if email else "",
            phone=phone.group(0).strip() if phone else "",
            location="",
            summary=" ".join(lines[1:3])[:300],
            total_years_experience=float(years) if years else None,
            skills=skills,
            experience=experience,
            education=education,
            certifications=[ln for ln in lines if "certified" in ln.lower()][:5],
            languages=[],
        )

    def assess(self, *, title, description, criteria, extraction, cv_text) -> CandidateAssessment:
        lines = _lines(cv_text)
        results: list[CriterionAssessment] = []
        for c in criteria:
            words = {w for w in re.findall(r"[a-z#.+]+", (c["label"] + " " + c["key"]).lower())
                     if len(w) > 1 and w not in STOPWORDS}
            hits = [ln for ln in lines if any(re.search(rf"(?<![\w]){re.escape(w)}(?![\w])", ln.lower())
                                              for w in words)]
            score = min(5, len(hits) + (1 if hits else 0))
            results.append(CriterionAssessment(
                key=c["key"], score=score, evidence=[h[:160] for h in hits[:2]],
                reasoning=(f"Found {len(hits)} CV line(s) mentioning: {', '.join(sorted(words))}."
                           if hits else "No matching evidence found in the CV."),
            ))
        strong = [r for r in results if r.score >= 3]
        weak = [r for r in results if r.score < 3]
        label = {c["key"]: c["label"] for c in criteria}
        return CandidateAssessment(
            criteria=results,
            strengths=[f"Evidence of {label[r.key]}" for r in strong][:5],
            gaps=[f"Limited evidence of {label[r.key]}" for r in weak][:5],
            interview_questions=[
                InterviewQuestion(
                    question=(f"Walk me through a project where you used {label[r.key]}." if r.score >= 3
                              else f"What exposure have you had to {label[r.key]}?"),
                    purpose="Verify depth of experience" if r.score >= 3 else "Probe a possible gap",
                    criterion_key=r.key,
                )
                for r in results
            ][:8],
        )
