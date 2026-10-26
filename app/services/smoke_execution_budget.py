from dataclasses import dataclass
from time import monotonic


SMOKE_EXECUTION_TIMEOUT_SECONDS = 240


class SmokeExecutionTimeoutError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "Smoke check exceeded the 240-second execution limit. Please try again."
        )


@dataclass(frozen=True)
class SmokeExecutionBudget:
    deadline_at: float

    @classmethod
    def start(
        cls,
        timeout_seconds: int = SMOKE_EXECUTION_TIMEOUT_SECONDS,
    ) -> "SmokeExecutionBudget":
        return cls(deadline_at=monotonic() + timeout_seconds)

    def limit_wait_timeout_ms(self, requested_timeout_ms: int) -> int:
        remaining_timeout_ms = int((self.deadline_at - monotonic()) * 1_000)
        if remaining_timeout_ms <= 0:
            raise SmokeExecutionTimeoutError
        return min(requested_timeout_ms, remaining_timeout_ms)

    def raise_if_expired(self) -> None:
        self.limit_wait_timeout_ms(1)
