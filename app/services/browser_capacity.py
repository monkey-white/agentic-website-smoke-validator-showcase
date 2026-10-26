from contextlib import contextmanager
from threading import BoundedSemaphore
from typing import Iterator


MAX_CONCURRENT_BROWSER_EXECUTIONS = 1


class BrowserExecutionBusyError(RuntimeError):
    pass


_browser_execution_slots = BoundedSemaphore(MAX_CONCURRENT_BROWSER_EXECUTIONS)


@contextmanager
def reserve_browser_execution() -> Iterator[None]:
    if not _browser_execution_slots.acquire(blocking=False):
        raise BrowserExecutionBusyError

    try:
        yield
    finally:
        _browser_execution_slots.release()
