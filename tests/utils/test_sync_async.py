import asyncio

from shared.utils.sync_async import run_async


async def _loop_identity() -> int:
    return id(asyncio.get_running_loop())


def test_run_async_reuses_same_event_loop():
    first = run_async(_loop_identity())
    second = run_async(_loop_identity())

    assert first == second
