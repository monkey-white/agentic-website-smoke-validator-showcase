import pytest

from app.models.browser_profile import BrowserEngine
from app.models.test_case import SmokeTestCase
from app.services.navigation import NavigationResult
from app.services.smoke_executor import (
    BrowserEngineUnavailableError,
    _evaluate_case,
    _is_safe_navigation_target,
    execute_smoke_test_plan,
)
from app.services.smoke_execution_budget import SmokeExecutionBudget
from playwright.sync_api import Error as PlaywrightError


class FakeMessage:
    type = "error"
    text = "Console error"


class FakeResponse:
    status = 404
    url = "https://example.com/missing"


class FakeLocator:
    def __init__(self, selector: str):
        self.selector = selector

    def count(self):
        if self.selector == "body:visible":
            return 1
        if "footer" in self.selector:
            return 1
        if self.selector.endswith(" >> a:visible"):
            return 2
        raise AssertionError(f"Unexpected selector: {self.selector}")

    def locator(self, selector: str):
        return FakeLocator(f"{self.selector} >> {selector}")

    def evaluate_all(self, _script: str):
        if self.selector.endswith(" >> a:visible"):
            return [
                "https://example.com/services",
                "https://example.com/login",
            ]
        if "footer" in self.selector:
            return [
                {
                    "tagName": "div",
                    "id": "ContainerFooter",
                    "className": "footer-wrapper",
                }
            ]
        return [{"text": "Contact", "url": "https://example.com/contact"}]

    @property
    def first(self):
        return self

    def wait_for(self, *, state: str, timeout: int):
        assert state == "visible"
        assert timeout == 5_000


class FakePage:
    def __init__(self):
        self.handlers = {}
        self.closed = False
        self.visited_urls = []

    def on(self, event: str, handler):
        self.handlers[event] = handler

    def goto(self, url: str, *, wait_until: str, timeout: int):
        self.visited_urls.append((url, wait_until, timeout))
        if "console" in self.handlers:
            self.handlers["console"](FakeMessage())
            self.handlers["response"](FakeResponse())

    def title(self):
        return "Example Business"

    @property
    def url(self):
        return self.visited_urls[-1][0]

    def locator(self, selector: str):
        return FakeLocator(selector)

    def close(self):
        self.closed = True


class DelayedNavigationLocator(FakeLocator):
    def count(self):
        if self.selector.endswith(" >> a:visible"):
            return 0
        return super().count()

    def locator(self, selector: str):
        return DelayedNavigationLocator(f"{self.selector} >> {selector}")


class DelayedNavigationPage(FakePage):
    def locator(self, selector: str):
        return DelayedNavigationLocator(selector)


class MissingTitlePage(FakePage):
    def title(self):
        return ""


class FakeBrowser:
    def __init__(self):
        self.pages = []
        self.closed = False
        self.version = "123.0.4567.0"

    def new_page(self, **_kwargs):
        page = FakePage()
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True


class DelayedNavigationBrowser(FakeBrowser):
    def new_page(self, **_kwargs):
        page = DelayedNavigationPage()
        self.pages.append(page)
        return page


class FakePlaywright:
    def __init__(self):
        self.browser = FakeBrowser()
        self.chromium = self
        self.firefox = self
        self.webkit = self
        self.launch_arguments = None

    def launch(self, *, headless: bool, **kwargs):
        assert headless is True
        self.launch_arguments = {"headless": headless, **kwargs}
        return self.browser


class FakePlaywrightContext:
    def __init__(self):
        self.playwright = FakePlaywright()

    def __enter__(self):
        return self.playwright

    def __exit__(self, *_args):
        return False


def _default_test_cases():
    return [
        SmokeTestCase(
            test_case_id=f"SMK-00{index}",
            title=f"Test {index}",
            priority="High",
            type="Smoke",
            preconditions=[],
            steps=[],
            expected_result="Expected result",
            automation_candidate=True,
        )
        for index in range(1, 6)
    ]


def test_execute_smoke_test_plan_runs_default_cases_with_safe_navigation(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.navigation.validate_public_url",
        lambda url: url,
    )
    test_cases = _default_test_cases()

    execution = execute_smoke_test_plan("https://example.com", test_cases)
    results = execution.results

    assert [result.status for result in results] == ["Passed"] * 5
    assert execution.environment.browser_engine == "Chromium"
    assert execution.environment.browser_version == "123.0.4567.0"
    assert context.playwright.launch_arguments == {
        "headless": True,
        "chromium_sandbox": True,
    }
    assert execution.environment.viewport_width == 1280
    assert execution.environment.viewport_height == 720
    assert results[0].console_errors == ["Console error"]
    assert results[0].network_errors == ["404 https://example.com/missing"]
    visited_urls = [page.visited_urls[0][0] for page in context.playwright.browser.pages]
    assert visited_urls == [
        "https://example.com",
        "https://example.com/services",
        "https://example.com/contact",
    ]
    assert context.playwright.browser.closed is True


def test_execute_smoke_test_plan_records_navigation_warning(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.smoke_executor.navigate_to_page",
        lambda _page, _url, _budget: NavigationResult(
            loaded=True,
            duration_seconds=30.0,
            warning="Visible content was available after timeout.",
        ),
    )

    results = execute_smoke_test_plan(
        "https://example.com", _default_test_cases()
    ).results

    assert all(
        "Visible content was available after timeout." in result.notes
        for result in results
    )


def test_execute_smoke_test_plan_uses_selected_browser_engine(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )

    execution = execute_smoke_test_plan(
        "https://example.com",
        _default_test_cases(),
        BrowserEngine.FIREFOX,
    )

    assert execution.environment.browser_engine == "Firefox"
    assert context.playwright.launch_arguments == {"headless": True}


def test_execute_smoke_test_plan_reports_unavailable_browser_engine(monkeypatch):
    class UnavailableBrowser:
        def launch(self, *, headless: bool, **_kwargs):
            assert headless is True
            raise PlaywrightError("Browser is not installed")

    context = FakePlaywrightContext()
    context.playwright.webkit = UnavailableBrowser()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )

    with pytest.raises(
        BrowserEngineUnavailableError,
        match="WebKit is not available on this server.",
    ):
        execute_smoke_test_plan(
            "https://example.com",
            _default_test_cases(),
            BrowserEngine.WEBKIT,
        )


def test_execute_smoke_test_plan_uses_one_navigation_snapshot_for_related_cases(
    monkeypatch,
):
    context = FakePlaywrightContext()
    context.playwright.browser = DelayedNavigationBrowser()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.navigation.validate_public_url",
        lambda url: url,
    )

    results = execute_smoke_test_plan(
        "https://example.com", _default_test_cases()
    ).results

    assert results[1].status == "Passed"
    assert results[1].actual_result == "Found 1 visible same-origin navigation links."
    assert results[2].status == "Passed"
    assert results[2].actual_result == "Loaded 1 selected navigation links."


def test_execute_smoke_test_plan_records_initial_navigation_duration(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.smoke_executor.navigate_to_page",
        lambda _page, _url, _budget: NavigationResult(
            loaded=False,
            duration_seconds=30.0,
            error="Timed out",
        ),
    )

    results = execute_smoke_test_plan(
        "https://example.com", _default_test_cases()
    ).results

    assert [result.status for result in results] == ["Failed"] * 5
    assert all(result.duration_seconds == 30.0 for result in results)
    assert all(result.notes == ["Timed out"] for result in results)


def test_homepage_failure_describes_the_missing_condition():
    passed, actual_result, _notes = _evaluate_case(
        "SMK-001",
        MissingTitlePage(),
        FakeBrowser(),
        "https://example.com",
        [],
        SmokeExecutionBudget.start(),
    )

    assert passed is False
    assert actual_result == "Homepage is missing a page title."


def test_footer_check_accepts_visible_footer_container_identified_by_id():
    passed, actual_result, _notes = _evaluate_case(
        "SMK-005",
        FakePage(),
        FakeBrowser(),
        "https://example.com",
        [],
        SmokeExecutionBudget.start(),
    )

    assert passed is True
    assert actual_result == "Found visible footer container: #ContainerFooter."


@pytest.mark.parametrize(
    "target_url",
    [
        "https://example.com/login.php",
        "https://example.com/account.php",
        "https://example.com/cart.php",
        "https://example.com/checkout/confirm",
    ],
)
def test_sensitive_legacy_navigation_paths_are_excluded(target_url):
    assert _is_safe_navigation_target(target_url, "https://example.com") is False
