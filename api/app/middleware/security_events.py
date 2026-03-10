"""Security event middleware — captures and logs all attack signals.

Logs structured JSON security events for:
- Rate limit violations (429)
- Authentication failures on /internal (403)
- Oversized payloads (413)
- Suspicious request patterns (path traversal, injection probes)

Each event is written via the shared structlog logger with event="security_event"
so it can be forwarded to any log aggregator (Loki, CloudWatch, Datadog, etc.)
"""

import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.logging import log

# Patterns that indicate active probing / attack attempts
_SUSPICIOUS_PATTERNS: list[tuple[str, str]] = [
    (r"\.\./", "path_traversal"),
    (r"%2e%2e%2f", "path_traversal_encoded"),
    (r"(?i)(union\s+select|select\s+.*\s+from|drop\s+table|insert\s+into)", "sql_injection"),
    (r"(?i)<script[\s>]", "xss_probe"),
    (r"(?i)(etc/passwd|etc/shadow|proc/self)", "lfi_probe"),
    (r"(?i)(cmd\.exe|powershell|/bin/sh|/bin/bash)", "rce_probe"),
    (r"(?i)(ignore\s+all\s+previous|ignore\s+previous\s+instructions)", "prompt_injection"),
]

_COMPILED = [(re.compile(pat), label) for pat, label in _SUSPICIOUS_PATTERNS]

# Max body bytes to scan for suspicious patterns (avoids reading huge payloads)
_SCAN_LIMIT = 4096


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _detect_suspicious(text: str) -> list[str]:
    return [label for pattern, label in _COMPILED if pattern.search(text)]


class SecurityEventsMiddleware(BaseHTTPMiddleware):
    """Observability layer: logs security events without blocking legitimate traffic."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        client_ip = _extract_client_ip(request)
        path = request.url.path
        method = request.method
        user_agent = request.headers.get("User-Agent", "")

        # --- Pre-request: scan URL + query string for suspicious patterns ---
        scan_target = f"{path}?{request.url.query}" if request.url.query else path
        url_threats = _detect_suspicious(scan_target)
        if url_threats:
            log.warning(
                "security_event",
                event_type="suspicious_url",
                threats=url_threats,
                client_ip=client_ip,
                path=path,
                method=method,
                user_agent=user_agent,
            )

        # --- Pre-request: scan request body for POST/PUT/PATCH ---
        body_threats: list[str] = []
        content_length = request.headers.get("Content-Length")
        if method in ("POST", "PUT", "PATCH"):
            if content_length and int(content_length) > 10 * 1024 * 1024:
                # Log oversized payload before FastAPI rejects it
                log.warning(
                    "security_event",
                    event_type="oversized_payload",
                    content_length=content_length,
                    client_ip=client_ip,
                    path=path,
                    method=method,
                    user_agent=user_agent,
                )
            # Only scan small payloads for patterns (avoid buffering huge requests)
            if not content_length or int(content_length) <= _SCAN_LIMIT:
                try:
                    body_bytes = await request.body()
                    body_threats = _detect_suspicious(body_bytes.decode("utf-8", errors="ignore"))
                    if body_threats:
                        log.warning(
                            "security_event",
                            event_type="suspicious_body",
                            threats=body_threats,
                            client_ip=client_ip,
                            path=path,
                            method=method,
                            user_agent=user_agent,
                        )
                except Exception:
                    pass

        # --- Execute request ---
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        # --- Post-request: log security-relevant response codes ---
        status = response.status_code

        if status == 429:
            log.warning(
                "security_event",
                event_type="rate_limit_hit",
                client_ip=client_ip,
                path=path,
                method=method,
                user_agent=user_agent,
                duration_ms=duration_ms,
            )
        elif status == 403 and path.startswith("/internal"):
            log.warning(
                "security_event",
                event_type="internal_auth_failure",
                client_ip=client_ip,
                path=path,
                method=method,
                user_agent=user_agent,
                duration_ms=duration_ms,
            )
        elif status == 413:
            log.warning(
                "security_event",
                event_type="payload_too_large",
                client_ip=client_ip,
                path=path,
                method=method,
                content_length=content_length,
                user_agent=user_agent,
                duration_ms=duration_ms,
            )
        elif status == 422 and (url_threats or body_threats):
            # Validation error on a suspicious request — likely a probe
            log.warning(
                "security_event",
                event_type="probe_validation_error",
                threats=url_threats + body_threats,
                client_ip=client_ip,
                path=path,
                method=method,
                user_agent=user_agent,
                duration_ms=duration_ms,
            )

        return response
