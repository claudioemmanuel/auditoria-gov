import asyncio
from threading import Lock
from typing import Coroutine, TypeVar

T = TypeVar("T")
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = Lock()


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
        return _loop


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Run an async coroutine from synchronous code (e.g. Celery tasks).

    We intentionally reuse a per-process event loop so async DB pools
    (e.g. asyncpg) are not shared across different loops.
    """
    loop = _get_or_create_loop()
    return loop.run_until_complete(coro)
