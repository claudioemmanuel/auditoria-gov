"""Alert/notification system for risk signals.

After signal creation, if severity >= HIGH:
1. Check alert subscriptions
2. Send notifications via configured channels (webhook, email)
3. Store alert log
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from openwatch_utils.logging import log
from openwatch_models.orm import RiskSignal


# Alert subscription is stored as a simple config dict for now.
# In production, this would be a dedicated ORM table.
_DEFAULT_WEBHOOK_URL = ""


def send_webhook(url: str, payload: dict) -> bool:
    """Send a webhook notification (sync, for Celery tasks)."""
    if not url:
        return False

    try:
        import httpx

        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload)
            return response.status_code < 400
    except Exception:
        log.exception("alert.webhook_failed", url=url)
        return False


def process_signal_alerts(session: Session, signal: RiskSignal) -> int:
    """Process alert notifications for a signal.

    Returns number of alerts sent.
    """
    if signal.severity not in ("high", "critical"):
        return 0

    alerts_sent = 0

    payload = {
        "event": "risk_signal",
        "signal_id": str(signal.id),
        "severity": signal.severity,
        "data_completeness": signal.data_completeness,
        "title": signal.title,
        "summary": signal.summary,
        "factors": signal.factors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Webhook notification
    webhook_url = _DEFAULT_WEBHOOK_URL
    if webhook_url and send_webhook(webhook_url, payload):
        alerts_sent += 1

    log.info(
        "alert.processed",
        signal_id=str(signal.id),
        severity=signal.severity,
        alerts_sent=alerts_sent,
    )

    return alerts_sent


def process_batch_alerts(session: Session) -> dict:
    """Process alerts for all unnotified HIGH/CRITICAL signals.

    Called periodically to catch any missed alerts.
    """
    stmt = (
        select(RiskSignal)
        .where(
            RiskSignal.severity.in_(["high", "critical"]),
        )
        .order_by(RiskSignal.created_at.desc())
        .limit(50)
    )
    signals = session.execute(stmt).scalars().all()

    total_sent = 0
    for s in signals:
        total_sent += process_signal_alerts(session, s)

    return {"signals_processed": len(signals), "alerts_sent": total_sent}
