"""Test setup: SQLite database, offline AI provider, n8n disabled.

Environment variables must be set *before* the app is imported, because settings and the
database engine are created at import time.
"""
import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="recruit-tests-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp / 'test.db'}",
    AI_PROVIDER="fake",
    N8N_WEBHOOK_URL="",
    UPLOAD_DIR=str(_tmp / "uploads"),
)

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(50, 50, 545, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data
