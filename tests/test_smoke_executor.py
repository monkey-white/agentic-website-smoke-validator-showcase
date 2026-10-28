import pytest

from app.models.browser_profile import BrowserEngine
from app.models.site_profile import SiteProfile
from app.models.test_case import SmokeTestCase
from app.services.navigation import NavigationResult
from app.services.smoke_executor import (
    BrowserEngineUnavailableError,
    _evaluate_case,
    _is_safe_navigation_target,
    execute_smoke_test_plan,
)
from app.services import smoke_executor
from app.services.smoke_execution_budget import SmokeExecutionBudget
from app.services.test_planner import create_default_smoke_test_plan
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
        if self.selector == "form:visible":
            return 0
        if "footer" in self.selector:
            return 1
        if self.selector.endswith(" >> a:visible"):
            return 2
        raise AssertionError(f"Unexpected selector: {self.selector}")

    def locator(self, selector: str):
        return FakeLocator(f"{self.selector} >> {selector}")

    def evaluate_all(self, _script: str):
        if self.selector in {
            "form:visible",
            "img:visible",
            "a[href]:visible",
            "button:visible, input[type='button']:visible, input[type='submit']:visible, input[type='reset']:visible",
        }:
            return []
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

    def evaluate(self, _script: str):
        return {
            "documentLanguage": "en",
            "responsiveViewport": True,
            "visibleMainCount": 1,
            "visibleH1Count": 1,
            "headingLevels": [1, 2],
            "horizontalOverflow": False,
            "descriptionPresent": True,
            "descriptionHasText": True,
            "hasTimedRefresh": False,
            "duplicateIdCount": 0,
        }

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
    site_profile = SiteProfile(
        website_url="https://example.com",
        detected_website_type="Business Website",
        detected_browser="Chromium",
        smoke_scope="Basic Business Website Smoke Validation",
        selected_test_count="20",
    )
    return create_default_smoke_test_plan(site_profile)


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
    monkeypatch.setattr(smoke_executor, "_visible_form_count", lambda _page: 0)
    monkeypatch.setattr(smoke_executor, "_visible_form_control_labels", lambda _page: [])
    test_cases = _default_test_cases()

    execution = execute_smoke_test_plan("https://example.com", test_cases)
    results = execution.results

    assert len(results) == 20
    assert all(result.status == "Passed" for result in results if result.test_case_id in {
        "SMK-001", "SMK-002", "SMK-003", "SMK-004", "SMK-005",
        "SMK-010", "SMK-011", "SMK-012", "SMK-013", "SMK-014",
        "SMK-017", "SMK-018", "SMK-019", "SMK-020",
    })
    assert all(result.status == "Skipped" for result in results if result.test_case_id in {
        "SMK-006", "SMK-007", "SMK-008", "SMK-009", "SMK-015", "SMK-016",
    })
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


def test_execute_smoke_test_plan_adds_form_check_when_a_form_is_visible(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.navigation.validate_public_url",
        lambda url: url,
    )
    monkeypatch.setattr(smoke_executor, "_visible_form_count", lambda _page: 1)
    monkeypatch.setattr(smoke_executor, "_visible_form_control_labels", lambda _page: [])

    execution = execute_smoke_test_plan("https://example.com", _default_test_cases())

    form_result = next(
        result for result in execution.results if result.test_case_id == "SMK-006"
    )
    assert form_result.status == "Passed"
    assert form_result.actual_result == (
        "Found 1 visible form(s); no data was entered or submitted."
    )


def test_execute_smoke_test_plan_adds_label_check_when_form_controls_exist(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.navigation.validate_public_url",
        lambda url: url,
    )
    monkeypatch.setattr(smoke_executor, "_visible_form_count", lambda _page: 1)
    monkeypatch.setattr(
        smoke_executor,
        "_visible_form_control_labels",
        lambda _page: [True, False],
    )

    execution = execute_smoke_test_plan("https://example.com", _default_test_cases())

    label_result = next(
        result for result in execution.results if result.test_case_id == "SMK-007"
    )
    assert label_result.status == "Failed"
    assert label_result.actual_result == (
        "Found 1 of 2 visible form control(s) without an accessible name."
    )


def test_execute_smoke_test_plan_adds_image_check_when_visible_images_exist(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.navigation.validate_public_url",
        lambda url: url,
    )
    monkeypatch.setattr(smoke_executor, "_visible_form_count", lambda _page: 0)
    monkeypatch.setattr(smoke_executor, "_visible_form_control_labels", lambda _page: [])
    monkeypatch.setattr(
        smoke_executor,
        "_visible_image_alternatives",
        lambda _page: [True, False],
    )

    execution = execute_smoke_test_plan("https://example.com", _default_test_cases())

    image_result = next(
        result for result in execution.results if result.test_case_id == "SMK-008"
    )
    assert image_result.status == "Failed"
    assert image_result.actual_result == (
        "Found 1 of 2 visible image(s) without alternative text or decorative markup."
    )


def test_execute_smoke_test_plan_adds_link_check_when_visible_links_exist(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.smoke_executor.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.navigation.validate_public_url",
        lambda url: url,
    )
    monkeypatch.setattr(smoke_executor, "_visible_form_count", lambda _page: 0)
    monkeypatch.setattr(smoke_executor, "_visible_form_control_labels", lambda _page: [])
    monkeypatch.setattr(smoke_executor, "_visible_image_alternatives", lambda _page: [])
    monkeypatch.setattr(
        smoke_executor,
        "_visible_link_accessible_names",
        lambda _page: [True, False],
    )

    execution = execute_smoke_test_plan("https://example.com", _default_test_cases())

    link_result = next(
        result for result in execution.results if result.test_case_id == "SMK-009"
    )
    assert link_result.status == "Failed"
    assert link_result.actual_result == (
        "Found 1 of 2 visible link(s) without an accessible name."
    )


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

    assert [result.status for result in results] == ["Failed"] * 20
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
