import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

log = logging.getLogger("slope.tasks")


def spawn_background(coro: Coroutine[Any, Any, None]) -> None:
    """Schedule async work without blocking the HTTP response (e.g. webhook pipeline).

    Exceptions are logged when the task completes; they do not propagate to the caller.
    """
    task = asyncio.create_task(coro)

    def _done(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            log.error(
                "Background task failed: %s",
                exc,
                exc_info=(type(exc), exc, exc.__traceback__),
            )

    task.add_done_callback(_done)
