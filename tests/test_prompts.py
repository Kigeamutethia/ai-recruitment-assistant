from app.ai.fake import FakeProvider
from app.ai.prompts import anonymised_profile, build_assess_prompt, redact

CV = """Jane Doe
jane.doe@example.com | +44 7700 900999
Python Developer, Acme, 2019 - 2024
Jane built FastAPI services."""


def test_redaction_removes_identifiers():
    ex = FakeProvider().extract_profile(CV)
    out = redact(CV, ex)
    assert "Jane" not in out and "Doe" not in out
    assert "jane.doe@example.com" not in out and "+44 7700 900999" not in out
    assert "FastAPI" in out


def test_assess_prompt_has_no_personal_details():
    ex = FakeProvider().extract_profile(CV)
    prompt = build_assess_prompt("Dev", "Build APIs", [{"key": "py", "label": "Python"}], ex, CV)
    assert "Jane" not in prompt and "example.com" not in prompt
    assert "full_name" not in anonymised_profile(ex)
