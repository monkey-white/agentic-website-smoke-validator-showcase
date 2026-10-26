from dataclasses import dataclass
from time import perf_counter

from playwright.sync_api import Error, Page, TimeoutError as PlaywrightTimeoutError

from app.services.smoke_execution_budget import SmokeExecutionBudget
from app.services.url_validator import validate_public_url


NAVIGATION_TIMEOUT_MS = 30_000


@dataclass(frozen=True)
class NavigationResult:
    loaded: bool
    duration_seconds: float
    warning: str | None = None
    error: str | None = None


def navigate_to_page(
    page: Page,
    website_url: str,
    execution_budget: SmokeExecutionBudget | None = None,
) -> NavigationResult:
    started_at = perf_counter()
    try:
        validate_public_url(website_url)
    except ValueError as error:
        return NavigationResult(
            loaded=False,
            duration_seconds=round(perf_counter() - started_at, 3),
            error=str(error),
        )

    try:
        page.goto(
            website_url,
            wait_until="domcontentloaded",
            timeout=(
                execution_budget.limit_wait_timeout_ms(NAVIGATION_TIMEOUT_MS)
                if execution_budget
                else NAVIGATION_TIMEOUT_MS
            ),
        )
    except PlaywrightTimeoutError as error:
        if execution_budget:
            execution_budget.raise_if_expired()
        duration_seconds = round(perf_counter() - started_at, 3)
        if page.locator("body:visible").count() > 0:
            return _validated_navigation_result(
                page,
                duration_seconds,
                warning=(
                    "Page navigation exceeded the DOMContentLoaded timeout, "
                    "but visible page content was available."
                ),
            )
        return NavigationResult(
            loaded=False,
            duration_seconds=duration_seconds,
            error=str(error),
        )
    except Error as error:
        return NavigationResult(
            loaded=False,
            duration_seconds=round(perf_counter() - started_at, 3),
            error=str(error),
        )

    if execution_budget:
        execution_budget.raise_if_expired()
    return _validated_navigation_result(
        page,
        round(perf_counter() - started_at, 3),
    )


def _validated_navigation_result(
    page: Page,
    duration_seconds: float,
    warning: str | None = None,
) -> NavigationResult:
    try:
        validate_public_url(page.url)
    except ValueError as error:
        return NavigationResult(
            loaded=False,
            duration_seconds=duration_seconds,
            error=f"Navigation reached a blocked destination: {error}",
        )

    return NavigationResult(
        loaded=True,
        duration_seconds=duration_seconds,
        warning=warning,
    )
