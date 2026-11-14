"""The AI provider interface and factory.

The rest of the app depends only on `LLMProvider`, never on a vendor SDK. Swapping Gemini for
another model (or for the offline fake in tests) is a one-line config change.
"""
from typing import Protocol

from ..config import get_settings
from .schemas import CandidateAssessment, CandidateExtraction


class LLMProvider(Protocol):
    model_name: str

    def extract_profile(self, cv_text: str) -> CandidateExtraction: ...

    def assess(self, *, title: str, description: str, criteria: list[dict],
               extraction: CandidateExtraction, cv_text: str) -> CandidateAssessment: ...


def get_provider() -> LLMProvider:
    s = get_settings()
    choice = s.ai_provider.lower()
    if choice == "auto":
        choice = "gemini" if s.gemini_api_key else "fake"
    if choice == "gemini":
        if not s.gemini_api_key:
            raise RuntimeError("AI_PROVIDER=gemini but GEMINI_API_KEY is not set")
        from .gemini import GeminiProvider

        return GeminiProvider(api_key=s.gemini_api_key, model=s.gemini_model)
    if choice == "fake":
        from .fake import FakeProvider

        return FakeProvider()
    raise RuntimeError(f"Unknown AI_PROVIDER: {s.ai_provider}")


def provider_name() -> str:
    s = get_settings()
    if s.ai_provider == "auto":
        return f"gemini:{s.gemini_model}" if s.gemini_api_key else "fake-heuristic"
    return f"gemini:{s.gemini_model}" if s.ai_provider == "gemini" else "fake-heuristic"
