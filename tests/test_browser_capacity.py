import pytest

from app.services.browser_capacity import (
    BrowserExecutionBusyError,
    reserve_browser_execution,
)


def test_browser_execution_reservation_allows_only_one_task():
    with reserve_browser_execution():
        with pytest.raises(BrowserExecutionBusyError):
            with reserve_browser_execution():
                pass

    with reserve_browser_execution():
        pass
