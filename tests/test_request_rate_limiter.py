import pytest

from app.services.request_rate_limiter import (
    DailyUsageCap,
    InMemoryRequestRateLimiter,
    RequestRateLimitError,
)


def test_rate_limiter_rejects_requests_over_the_window_limit():
    limiter = InMemoryRequestRateLimiter(max_requests=2, window_seconds=60)

    limiter.enforce("203.0.113.10")
    limiter.enforce("203.0.113.10")

    with pytest.raises(RequestRateLimitError) as error:
        limiter.enforce("203.0.113.10")

    assert error.value.retry_after_seconds > 0


def test_rate_limiter_keeps_clients_separate():
    limiter = InMemoryRequestRateLimiter(max_requests=1, window_seconds=60)

    limiter.enforce("203.0.113.10")
    limiter.enforce("203.0.113.11")


def test_daily_usage_cap_stops_requests_after_its_limit():
    cap = DailyUsageCap(maximum_uses=2)

    assert cap.reserve() is True
    assert cap.reserve() is True
    assert cap.reserve() is False
