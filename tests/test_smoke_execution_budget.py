import pytest

from app.services.smoke_execution_budget import (
    SmokeExecutionBudget,
    SmokeExecutionTimeoutError,
)


def test_execution_budget_limits_wait_to_remaining_time(monkeypatch):
    monkeypatch.setattr(
        "app.services.smoke_execution_budget.monotonic",
        lambda: 100.0,
    )
    budget = SmokeExecutionBudget(deadline_at=101.5)

    assert budget.limit_wait_timeout_ms(30_000) == 1_500


def test_execution_budget_rejects_expired_runs(monkeypatch):
    monkeypatch.setattr(
        "app.services.smoke_execution_budget.monotonic",
        lambda: 100.0,
    )
    budget = SmokeExecutionBudget(deadline_at=100.0)

    with pytest.raises(SmokeExecutionTimeoutError):
        budget.raise_if_expired()
