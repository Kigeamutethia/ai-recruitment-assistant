# n8n automation

n8n handles notifications and reporting. It sits **outside the critical path**: the backend
sends events to it as a best-effort step, so if n8n is down, CV analysis still works.

## Workflows

| File | Trigger | What it does |
|---|---|---|
| `workflows/recruitment-events.json` | Webhook `POST /webhook/recruitment-events` | Formats backend events into a notification and emails the recruiter |
| `workflows/daily-digest.json` | Weekdays 08:00 (plus a manual trigger) | Calls `GET /api/reports/summary` and emails a digest of open jobs and top candidates |

Events sent by the backend ([`backend/app/services/events.py`](../backend/app/services/events.py)):

| Event | When |
|---|---|
| `application.analysed` | A CV has been scored |
| `application.failed` | Text extraction or AI analysis failed |
| `batch.completed` | Every CV from one upload has finished |
| `review.created` | A recruiter recorded a decision |

The payload is `{"event": "...", "sent_at": "...", "data": {...}}`.

## Import and publish

```bash
docker compose exec n8n n8n import:workflow --separate --input=/workflows
docker compose exec n8n n8n publish:workflow --id=RecruitEvents001
docker compose exec n8n n8n publish:workflow --id=RecruitDigest001
docker compose restart n8n
```

Then open http://localhost:5678 (or your `N8N_PORT`), create the owner account, and open
**Executions** to see each event the backend sends.

## Turning on email

The email nodes ship **disabled** so the workflows can be published without credentials.

1. In n8n, go to **Credentials → New → SMTP**. Any SMTP provider works (Gmail app password,
   Mailtrap, SendGrid and so on).
2. Open each workflow, select the *Email* node, attach the credential and set the *From* address.
3. Enable the node and publish the workflow again.
4. Set `RECRUITER_EMAIL` in `.env` and run `docker compose up -d n8n`.

## Editing workflows

Make your changes in the n8n UI, then export them back so the repo stays the source of truth:

```bash
docker compose exec n8n n8n export:workflow --id=RecruitEvents001 --pretty --output=/tmp/w.json
docker compose cp n8n:/tmp/w.json automation/workflows/recruitment-events.json
```
