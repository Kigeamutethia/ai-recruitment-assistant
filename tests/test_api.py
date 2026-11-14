"""End-to-end API tests using the offline AI provider."""
from conftest import make_pdf
from samples import CVS, JOB


def _create_job(client, **overrides):
    r = client.post("/api/jobs", json={**JOB, **overrides})
    assert r.status_code == 201, r.text
    return r.json()


def _upload(client, job_id, files: dict[str, bytes]):
    return client.post(f"/api/jobs/{job_id}/applications",
                       files=[("files", (n, d, "application/pdf")) for n, d in files.items()])


def test_health(client):
    r = client.get("/api/health")
    assert r.json()["status"] == "ok" and r.json()["ai_provider"] == "fake-heuristic"


def test_create_job_generates_unique_keys(client):
    job = _create_job(client, criteria=[{"label": "Python skills"}, {"label": "Python skills"}])
    assert [c["key"] for c in job["criteria"]] == ["python_skills", "python_skills_2"]


def test_full_pipeline_ranks_candidates(client):
    job = _create_job(client)
    r = _upload(client, job["id"], {n: make_pdf(t) for n, t in CVS.items()})
    assert r.status_code == 202 and len(r.json()["accepted"]) == 4

    # TestClient runs background tasks before returning, so analysis is already done.
    ranked = client.get(f"/api/jobs/{job['id']}/applications").json()
    assert all(a["status"] == "analysed" for a in ranked)
    scores = [a["overall_score"] for a in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0]["candidate_name"] == "Amara Okafor"  # strongest fictional CV
    assert ranked[-1]["candidate_name"] == "Kwame Mensah"

    detail = client.get(f"/api/applications/{ranked[0]['id']}").json()
    assert detail["candidate"]["email"] == "amara.okafor@example.com"
    assert len(detail["assessment"]["criteria"]) == len(JOB["criteria"])
    assert detail["assessment"]["interview_questions"]
    assert detail["profile"]["model_name"] == "fake-heuristic"


def test_upload_rejects_non_pdf_and_duplicates(client):
    job = _create_job(client)
    pdf = make_pdf(CVS["liam_chen.pdf"])
    r = client.post(f"/api/jobs/{job['id']}/applications", files=[
        ("files", ("a.pdf", pdf, "application/pdf")),
        ("files", ("b.pdf", pdf, "application/pdf")),
        ("files", ("notes.txt", b"hello", "text/plain")),
    ])
    body = r.json()
    assert len(body["accepted"]) == 1
    assert {x["filename"] for x in body["rejected"]} == {"b.pdf", "notes.txt"}


def test_empty_pdf_fails_gracefully(client):
    job = _create_job(client)
    _upload(client, job["id"], {"scan.pdf": make_pdf(" ")})
    [app] = client.get(f"/api/jobs/{job['id']}/applications").json()
    assert app["status"] == "failed" and "scanned" in app["failure_reason"]


def test_reweighting_is_applied_on_read(client):
    job = _create_job(client)
    _upload(client, job["id"], {n: make_pdf(t) for n, t in CVS.items()})
    before = {a["candidate_name"]: a["overall_score"] for a in client.get(f"/api/jobs/{job['id']}/applications").json()}

    criteria = [{**c, "weight": 10 if c["key"] == "sql" else 0.1} for c in JOB["criteria"]]
    client.patch(f"/api/jobs/{job['id']}", json={"criteria": criteria})
    after = {a["candidate_name"]: a["overall_score"] for a in client.get(f"/api/jobs/{job['id']}/applications").json()}
    assert before != after


def test_review_changes_status_and_is_audited(client):
    job = _create_job(client)
    _upload(client, job["id"], {"amara.pdf": make_pdf(CVS["amara_okafor.pdf"])})
    [app] = client.get(f"/api/jobs/{job['id']}/applications").json()

    r = client.post(f"/api/applications/{app['id']}/reviews",
                    json={"reviewer": "recruiter@example.com", "decision": "shortlisted", "notes": "Strong APIs"})
    assert r.status_code == 201
    detail = client.get(f"/api/applications/{app['id']}").json()
    assert detail["status"] == "shortlisted" and detail["reviews"][0]["notes"] == "Strong APIs"


def test_reanalyse_keeps_history(client):
    job = _create_job(client)
    _upload(client, job["id"], {"sofia.pdf": make_pdf(CVS["sofia_marquez.pdf"])})
    [app] = client.get(f"/api/jobs/{job['id']}/applications").json()
    assert client.post(f"/api/applications/{app['id']}/reanalyse").status_code == 202

    import uuid

    from app.db import SessionLocal
    from app.models import Assessment
    with SessionLocal() as db:
        assert db.query(Assessment).filter_by(application_id=uuid.UUID(app["id"])).count() == 2


def test_report_summary(client):
    job = _create_job(client)
    _upload(client, job["id"], {n: make_pdf(t) for n, t in CVS.items()})
    report = client.get("/api/reports/summary").json()
    [j] = report["open_jobs"]
    assert j["total_applications"] == 4 and j["new_last_24h"] == 4 and len(j["top_candidates"]) == 3


def test_events_are_posted_to_n8n(client, monkeypatch):
    from app.config import get_settings
    import app.services.events as events

    sent = []
    monkeypatch.setattr(get_settings(), "n8n_webhook_url", "http://n8n.test/webhook")

    class _Resp:
        def raise_for_status(self): return self

    monkeypatch.setattr(events.httpx, "post", lambda url, json, timeout: sent.append((url, json)) or _Resp())
    job = _create_job(client)
    _upload(client, job["id"], {"amara.pdf": make_pdf(CVS["amara_okafor.pdf"])})

    kinds = [body["event"] for _, body in sent]
    assert kinds == ["application.analysed", "batch.completed"]
    assert sent[0][0] == "http://n8n.test/webhook/recruitment-events"
