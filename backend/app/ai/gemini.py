"""Google Gemini implementation of LLMProvider, using the `google-genai` SDK.

Key technique: structured output. We pass a Pydantic model as `response_schema` and set
`response_mime_type="application/json"`, so Gemini must return JSON matching our schema.
"""
import logging
import time
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from .prompts import build_assess_prompt, build_extract_prompt
from .schemas import CandidateAssessment, CandidateExtraction

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

# HTTP codes not worth retrying: bad request, auth, not found.
_NON_RETRYABLE = {400, 401, 403, 404}
MAX_OUTPUT_TOKENS = 8192  # a full assessment is ~1-2k tokens; leaves room for thinking


class GeminiProvider:
    def __init__(self, api_key: str, model: str, max_attempts: int = 3):
        # Without a timeout a stalled request blocks the pipeline forever (ms).
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=300_000))
        self.model_name = model
        self._max_attempts = max_attempts

    def _generate(self, prompt: str, schema: type[T]) -> T:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            # Temperature is left at the default: Google advises against lowering it for Gemini 3
            # models, which can then loop until they hit the output limit (slow AND costly).
            # Hard cap on output size: a runaway response can never burn more than this.
            max_output_tokens=MAX_OUTPUT_TOKENS,
            # Gemini 3.x "thinks" before answering. Extraction and evidence-matching don't need
            # deep reasoning; LOW keeps latency down and saves tokens.
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        )
        for attempt in range(1, self._max_attempts + 1):
            try:
                resp = self._client.models.generate_content(
                    model=self.model_name, contents=prompt, config=config
                )
                if isinstance(resp.parsed, schema):
                    return resp.parsed
                return schema.model_validate_json(resp.text or "")
            except errors.APIError as e:
                if e.code in _NON_RETRYABLE or attempt == self._max_attempts:
                    raise
                log.warning("Gemini API error %s (attempt %d), retrying", e.code, attempt)
            except ValidationError:
                if attempt == self._max_attempts:
                    raise
                log.warning("Gemini returned invalid JSON (attempt %d), retrying", attempt)
            time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s, ...
        raise RuntimeError("unreachable")

    def extract_profile(self, cv_text: str) -> CandidateExtraction:
        return self._generate(build_extract_prompt(cv_text), CandidateExtraction)

    def assess(self, *, title, description, criteria, extraction, cv_text) -> CandidateAssessment:
        prompt = build_assess_prompt(title, description, criteria, extraction, cv_text)
        return self._generate(prompt, CandidateAssessment)
