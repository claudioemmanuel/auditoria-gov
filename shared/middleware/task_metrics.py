"""Celery signal-based task metrics.

Hooks into task_prerun / task_postrun / task_failure to emit structured
logs with duration_ms, task name, queue, retry count, and outcome.
Also stores duration_ms in Redis sorted sets for /internal/metrics aggregation.
No decorator needed — just import this module from worker_app.py.
"""
import time
from threading import local

from celery.signals import task_failure, task_postrun, task_prerun, task_retry

from shared.logging import log

_state = local()

# Redis key pattern: task_metrics:{task_short_name}
# Sorted set: score = duration_ms, member = "{timestamp}:{task_id}"
_METRICS_KEY_PREFIX = "task_metrics:"
_METRICS_MAX_ENTRIES = 500  # Keep last 500 executions per task type


def _get_redis():
    """Lazy Redis connection for metrics storage."""
    try:
        import redis
        from shared.config import settings
        return redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _short_task_name(full_name: str) -> str:
    """Extract short name from fully qualified task name."""
    return full_name.rsplit(".", 1)[-1] if full_name else "unknown"


def _record_metric(task_name: str, duration_ms: float, outcome: str):
    """Store task execution metric in Redis sorted set."""
    r = _get_redis()
    if r is None:
        return
    try:
        short = _short_task_name(task_name)
        key = f"{_METRICS_KEY_PREFIX}{short}"
        ts = time.time()
        member = f"{ts:.3f}:{outcome}"
        r.zadd(key, {member: duration_ms})
        # Trim to keep only last N entries
        count = r.zcard(key)
        if count > _METRICS_MAX_ENTRIES:
            r.zremrangebyrank(key, 0, count - _METRICS_MAX_ENTRIES - 1)
        # Set TTL to 24h
        r.expire(key, 86400)
    except Exception:
        pass  # Metrics are best-effort


def get_task_metrics() -> dict[str, dict]:
    """Aggregate task metrics from Redis.

    Returns dict[task_name -> {count, p50, p95, p99, mean, failures}].
    """
    r = _get_redis()
    if r is None:
        return {}

    result = {}
    try:
        keys = r.keys(f"{_METRICS_KEY_PREFIX}*")
        for key in keys:
            task_name = key.replace(_METRICS_KEY_PREFIX, "")
            entries = r.zrangebyscore(key, "-inf", "+inf", withscores=True)
            if not entries:
                continue

            durations = [score for _, score in entries]
            failures = sum(1 for member, _ in entries if ":failure" in member)
            durations.sort()
            n = len(durations)

            result[task_name] = {
                "count": n,
                "failures": failures,
                "mean_ms": round(sum(durations) / n, 1),
                "p50_ms": round(durations[n // 2], 1),
                "p95_ms": round(durations[int(n * 0.95)], 1) if n > 1 else round(durations[0], 1),
                "p99_ms": round(durations[int(n * 0.99)], 1) if n > 1 else round(durations[0], 1),
                "min_ms": round(durations[0], 1),
                "max_ms": round(durations[-1], 1),
            }
    except Exception:
        pass

    return result


@task_prerun.connect
def _on_prerun(sender=None, task_id=None, task=None, **kwargs):
    _state.start = time.monotonic()


@task_postrun.connect
def _on_postrun(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
    start = getattr(_state, "start", None)
    duration_ms = round((time.monotonic() - start) * 1000, 1) if start else None

    task_name = task.name if task else "unknown"
    log.info(
        "task.completed",
        task=task_name,
        task_id=task_id,
        state=state,
        duration_ms=duration_ms,
        retries=task.request.retries if task else 0,
    )

    if duration_ms is not None:
        _record_metric(task_name, duration_ms, "success")

    _state.start = None


@task_failure.connect
def _on_failure(sender=None, task_id=None, exception=None, traceback=None, **kwargs):
    start = getattr(_state, "start", None)
    duration_ms = round((time.monotonic() - start) * 1000, 1) if start else None

    task_name = sender.name if sender else "unknown"
    log.error(
        "task.failed",
        task=task_name,
        task_id=task_id,
        duration_ms=duration_ms,
        error=str(exception),
        error_type=type(exception).__name__,
        retries=sender.request.retries if sender else 0,
    )

    if duration_ms is not None:
        _record_metric(task_name, duration_ms, "failure")

    _state.start = None


@task_retry.connect
def _on_retry(sender=None, request=None, reason=None, **kwargs):
    log.warning(
        "task.retry",
        task=sender.name if sender else "unknown",
        task_id=request.id if request else None,
        reason=str(reason),
        retries=(request.retries if request else 0) + 1,
    )
