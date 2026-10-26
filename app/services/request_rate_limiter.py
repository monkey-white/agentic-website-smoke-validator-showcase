from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, date
from hashlib import sha256
import logging
from secrets import token_bytes
from threading import Lock
from time import monotonic


SMOKE_RUN_LIMIT = 10
SMOKE_RUN_WINDOW_SECONDS = 60 * 60
DAILY_AI_ANALYSIS_LIMIT = 100
_PROCESS_SALT = token_bytes(32)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestRateLimitError(RuntimeError):
    retry_after_seconds: int


class InMemoryRequestRateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        minimum_interval_seconds: int = 0,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._minimum_interval_seconds = minimum_interval_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = Lock()

    def enforce(self, client_ip: str) -> None:
        client_key = sha256(_PROCESS_SALT + client_ip.encode()).hexdigest()
        current_time = monotonic()
        with self._lock:
            request_times = self._requests.setdefault(client_key, deque())
            while request_times and current_time - request_times[0] >= self._window_seconds:
                request_times.popleft()
            if (
                request_times
                and current_time - request_times[-1] < self._minimum_interval_seconds
            ):
                retry_after = int(
                    self._minimum_interval_seconds - (current_time - request_times[-1])
                ) + 1
                logger.warning("Smoke run rejected by the per-client cooldown.")
                raise RequestRateLimitError(retry_after)
            if len(request_times) >= self._max_requests:
                retry_after = int(self._window_seconds - (current_time - request_times[0])) + 1
                logger.warning("Smoke run rejected by the per-client rate limit.")
                raise RequestRateLimitError(retry_after)
            request_times.append(current_time)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


smoke_run_rate_limiter = InMemoryRequestRateLimiter(
    max_requests=SMOKE_RUN_LIMIT,
    window_seconds=SMOKE_RUN_WINDOW_SECONDS,
)


class DailyUsageCap:
    def __init__(self, maximum_uses: int) -> None:
        self._maximum_uses = maximum_uses
        self._current_day: date | None = None
        self._uses = 0
        self._lock = Lock()

    def reserve(self) -> bool:
        current_day = datetime.now(UTC).date()
        with self._lock:
            if self._current_day != current_day:
                self._current_day = current_day
                self._uses = 0
            if self._uses >= self._maximum_uses:
                logger.warning("AI diagnostic analysis rejected by the global daily cap.")
                return False
            self._uses += 1
            logger.info("AI diagnostic analysis reserved: daily_count=%s", self._uses)
            return True

    def reset(self) -> None:
        with self._lock:
            self._current_day = None
            self._uses = 0


daily_ai_analysis_cap = DailyUsageCap(DAILY_AI_ANALYSIS_LIMIT)
