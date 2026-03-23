"""Infrastructure alert dispatcher — separate from signal alerts.

Alert conditions fired by _send_infra_alert(event, **context):
  er_stale_recovered    — stale ER run auto-recovered (info)
  memory_throttle       — worker memory >= MEM_BLOCK_PCT (warning)
  cpu_high              — CPU >= CPU_WARN_PCT (warning)
  disk_throttle         — disk >= DISK_THROTTLE_PCT (warning)
  backlog_critical      — backlog ETA < BACKLOG_WARN_ETA_MINUTES (warning)
  dead_letter           — Celery task exhausted max_retries (error)
  pipeline_stalled      — no completed ingest in 24h (error)

Design contract:
  - Never raises. Alerting must not crash the pipeline.
  - Fail-open on Redis unavailability (send the alert, skip cooldown tracking).
  - Respects per-event cooldown to avoid notification spam.
  - No-ops silently when INFRA_ALERT_WEBHOOK_URL is not configured.
"""

import os
from datetime import datetime, timezone

from shared.logging import log

_INFRA_WEBHOOK: str = os.environ.get("INFRA_ALERT_WEBHOOK_URL", "")
_ALERT_COOLDOWN_SECONDS: int = int(os.environ.get("INFRA_ALERT_COOLDOWN_SECONDS", "1800"))


def _send_infra_alert(event: str, **context: object) -> bool:
    """Send an infrastructure alert webhook with per-event cooldown.

    Returns True if the alert was dispatched, False if suppressed or
    if the webhook is not configured.  Never raises.
    """
    if not _INFRA_WEBHOOK:
        return False

    cooldown_key = f"infra_alert:cooldown:{event}"

    # ── Cooldown check (fail-open: if Redis is down, still attempt to send) ──
    r = None
    try:
        import redis as redis_lib

        from shared.config import settings

        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        if r.get(cooldown_key):
            return False  # Already alerted recently
    except Exception:  # noqa: BLE001
        pass  # Redis unavailable — proceed to send anyway

    auto_resolved = bool(context.pop("auto_resolved", False))
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "openwatch",
        "auto_resolved": auto_resolved,
        **context,
    }

    # ── Send webhook ──────────────────────────────────────────────────────────
    try:
        import httpx

        httpx.post(_INFRA_WEBHOOK, json=payload, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        log.warning("infra_alert.failed", alert_event=event, error=str(exc))
        return False

    # ── Set cooldown after successful send (fail-open) ────────────────────────
    if r is not None:
        try:
            r.setex(cooldown_key, _ALERT_COOLDOWN_SECONDS, "1")
        except Exception:  # noqa: BLE001
            pass  # Redis unavailable — cooldown not set, but alert was sent

    log.info("infra_alert.sent", alert_event=event)
    return True
