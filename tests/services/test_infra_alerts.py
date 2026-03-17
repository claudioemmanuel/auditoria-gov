"""Tests for shared.services.infra_alerts._send_infra_alert.

Coverage:
- Webhook not configured → returns False, never raises
- Cooldown suppression → second call within window is not sent
- Successful send → returns True, cooldown key set
- auto_resolved=True field propagates in payload
- Webhook HTTP error → returns False, never raises
- Redis unavailable during cooldown check → fail-open, still sends
- Redis setex failure after send → swallowed, returns True
- Required payload fields (event, timestamp, service, auto_resolved) always present
"""
from unittest.mock import MagicMock, patch

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_redis_mock(*, has_cooldown: bool = False) -> MagicMock:
    r = MagicMock()
    r.get.return_value = b"1" if has_cooldown else None
    r.setex.return_value = True
    return r


def _capture_post_factory(captured: dict):
    """Return an httpx.post side_effect that stores the JSON payload."""

    def _capture(url, *, json=None, timeout=None):
        captured.update(json or {})
        return MagicMock()

    return _capture


# ── test cases ─────────────────────────────────────────────────────────────────


class TestSendInfraAlert:
    def test_webhook_not_configured_returns_false(self):
        import shared.services.infra_alerts as mod

        with patch.object(mod, "_INFRA_WEBHOOK", ""):
            result = mod._send_infra_alert("er_stale_recovered")

        assert result is False

    def test_webhook_not_configured_never_raises(self):
        import shared.services.infra_alerts as mod

        with patch.object(mod, "_INFRA_WEBHOOK", ""):
            mod._send_infra_alert("er_stale_recovered", er_id="abc-123")  # must not raise

    def test_cooldown_suppresses_second_call(self):
        import shared.services.infra_alerts as mod

        mock_redis = _make_redis_mock(has_cooldown=True)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
        ):
            result = mod._send_infra_alert("memory_throttle", pct=90)

        assert result is False
        mock_redis.get.assert_called_once_with("infra_alert:cooldown:memory_throttle")

    def test_successful_send_returns_true(self):
        import shared.services.infra_alerts as mod

        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", return_value=MagicMock()),
        ):
            result = mod._send_infra_alert("er_stale_recovered", source="watchdog")

        assert result is True

    def test_auto_resolved_true_propagates(self):
        import shared.services.infra_alerts as mod

        captured: dict = {}
        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", side_effect=_capture_post_factory(captured)),
        ):
            mod._send_infra_alert("er_stale_recovered", auto_resolved=True, er_id="abc-123")

        assert captured["auto_resolved"] is True
        assert captured["er_id"] == "abc-123"

    def test_auto_resolved_defaults_to_false(self):
        import shared.services.infra_alerts as mod

        captured: dict = {}
        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", side_effect=_capture_post_factory(captured)),
        ):
            mod._send_infra_alert("cpu_high", pct=90)

        assert captured["auto_resolved"] is False

    def test_webhook_http_error_returns_false(self):
        import shared.services.infra_alerts as mod

        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", side_effect=Exception("connection refused")),
        ):
            result = mod._send_infra_alert("cpu_high", pct=95)

        assert result is False

    def test_webhook_http_error_never_raises(self):
        import shared.services.infra_alerts as mod

        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", side_effect=ConnectionError("refused")),
        ):
            mod._send_infra_alert("disk_throttle", pct=95)  # must not raise

    def test_redis_unavailable_proceeds_to_send(self):
        import shared.services.infra_alerts as mod

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", side_effect=Exception("redis down")),
            patch("httpx.post", return_value=MagicMock()) as mock_post,
        ):
            result = mod._send_infra_alert("backlog_critical", current=900000)

        assert result is True
        mock_post.assert_called_once()

    def test_redis_setex_failure_swallowed_returns_true(self):
        import shared.services.infra_alerts as mod

        mock_redis = _make_redis_mock(has_cooldown=False)
        mock_redis.setex.side_effect = Exception("write failed")

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", return_value=MagicMock()),
        ):
            result = mod._send_infra_alert("er_stale_recovered")

        assert result is True  # swallowed — alert was still sent

    def test_payload_contains_required_fields(self):
        import shared.services.infra_alerts as mod

        captured: dict = {}
        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", side_effect=_capture_post_factory(captured)),
        ):
            mod._send_infra_alert("pipeline_stalled")

        assert captured["event"] == "pipeline_stalled"
        assert "timestamp" in captured
        assert captured["service"] == "auditoria-gov"
        assert "auto_resolved" in captured

    def test_cooldown_key_set_with_correct_name_and_ttl(self):
        import shared.services.infra_alerts as mod

        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch.object(mod, "_ALERT_COOLDOWN_SECONDS", 1800),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", return_value=MagicMock()),
        ):
            mod._send_infra_alert("dead_letter", task="some_task")

        mock_redis.setex.assert_called_once()
        key, ttl, val = mock_redis.setex.call_args[0]
        assert key == "infra_alert:cooldown:dead_letter"
        assert ttl == 1800
        assert val == "1"

    def test_extra_context_fields_included_in_payload(self):
        import shared.services.infra_alerts as mod

        captured: dict = {}
        mock_redis = _make_redis_mock(has_cooldown=False)

        with (
            patch.object(mod, "_INFRA_WEBHOOK", "https://example.com/hook"),
            patch("redis.from_url", return_value=mock_redis),
            patch("httpx.post", side_effect=_capture_post_factory(captured)),
        ):
            mod._send_infra_alert(
                "backlog_critical",
                current=950000,
                rate_per_min=5000.0,
                eta_minutes=10.0,
            )

        assert captured["current"] == 950000
        assert captured["rate_per_min"] == 5000.0
        assert captured["eta_minutes"] == 10.0
