"""Background task runner.

The UI must never freeze: anything that reads a file or crunches a
DataFrame runs through ``TaskRunner.submit`` on a worker thread, and
results are marshalled back to the Tk thread via callbacks (the UI layer
wraps them with ``widget.after``).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


class TaskRunner:
    """Small thread-pool wrapper with success/error callbacks."""

    def __init__(self, max_workers: int = 4) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="lendops")

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        on_done: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
        **kwargs: Any,
    ) -> Future:
        future = self._pool.submit(func, *args, **kwargs)

        def _finished(f: Future) -> None:
            exc = f.exception()
            if exc is not None:
                logger.error("background task %s failed: %s", func.__name__, exc)
                if on_error is not None:
                    on_error(exc)
            elif on_done is not None:
                on_done(f.result())

        future.add_done_callback(_finished)
        return future

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
