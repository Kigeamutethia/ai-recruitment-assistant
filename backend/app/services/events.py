"""Audit log + outbound events to n8n.

Every significant event is written to `audit_log` (inside the caller's transaction) and, after
commit, optionally POSTed to n8n. n8n is best-effort: if it is down we log and carry on —
automation must never break core processing.
"""
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AuditLog

log = logging.getLogger(__name__)
WEBHOOK_PATH = "recruitment-events"


def audit(db: Session, event_type: str, entity_type: str, entity_id: uuid.UUID | None,
          payload: dict | None = None, actor: str = "system") -> None:
    db.add(AuditLog(event_type=event_type, entity_type=entity_type, entity_id=entity_id,
                    payload=payload, actor=actor))


def emit(event_type: str, data: dict) -> None:
    base = get_settings().n8n_webhook_url
    if not base:
        return
    body = {"event": event_type, "sent_at": datetime.now(timezone.utc).isoformat(), "data": data}
    try:
        httpx.post(f"{base.rstrip('/')}/{WEBHOOK_PATH}", json=body, timeout=5).raise_for_status()
    except httpx.HTTPError as e:
        log.warning("n8n webhook failed for %s: %s", event_type, e)
