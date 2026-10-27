from importlib.metadata import version
from platform import system
import re
from time import perf_counter
from urllib.parse import urlparse

from playwright.sync_api import (
    Browser,
    ConsoleMessage,
    Error as PlaywrightError,
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from app.models.browser_profile import BrowserEngine
from app.models.smoke_result import SmokeTestResult
from app.models.test_execution import ExecutionEnvironment, SmokeTestExecution
from app.models.test_case import SmokeTestCase
from app.services.navigation import navigate_to_page
from app.services.browser_policy import browser_launch_options
from app.services.smoke_execution_budget import SmokeExecutionBudget
from app.services.test_planner import (
    create_form_accessibility_test_case,
    create_form_availability_test_case,
)


MAX_NAVIGATION_LINKS = 3
MAX_ERRORS = 20
NAVIGATION_SNAPSHOT_TIMEOUT_MS = 5_000
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}
NAVIGATION_CONTAINER_SELECTOR = (
    "nav:visible, [role='navigation']:visible, "
    "[id*='nav' i]:visible, [class*='nav' i]:visible, "
    "[id*='menu' i]:visible, [class*='menu' i]:visible"
)
FOOTER_CONTAINER_SELECTOR = (
    "footer:visible, [role='contentinfo']:visible, "
    "[id*='footer' i]:visible, [class*='footer' i]:visible"
)
SENSITIVE_PATH_KEYWORDS = {
    "account",
    "admin",
    "auth",
    "cart",
    "checkout",
    "login",
    "payment",
    "register",
    "sign-in",
    "signin",
    "signup",
}


class BrowserEngineUnavailableError(RuntimeError):
    def __init__(self, browser_engine: BrowserEngine):
        super().__init__(
            f"{browser_engine.display_name} is not available on this server."
        )


def execute_smoke_test_plan(
    website_url: str,
    test_cases: list[SmokeTestCase],
    browser_engine: BrowserEngine = BrowserEngine.CHROMIUM,
) -> SmokeTestExecution:
    console_errors: list[str] = []
    network_errors: list[str] = []
    execution_budget = SmokeExecutionBudget.start()

    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, browser_engine)
        try:
            execution_budget.raise_if_expired()
            environment = _create_execution_environment(browser, browser_engine)
            page = browser.new_page(viewport=DEFAULT_VIEWPORT)
            _register_error_listeners(page, console_errors, network_errors)
            navigation = navigate_to_page(page, website_url, execution_budget)
            if not navigation.loaded:
                return SmokeTestExecution(
                    results=[
                        _failed_navigation_result(
                            test_case,
                            navigation.error or "Homepage could not be loaded.",
                            navigation.duration_seconds,
                        )
                        for test_case in test_cases
                    ],
                    environment=environment,
                )

            test_cases = _select_adaptive_test_cases(page, test_cases)
            navigation_notes = [navigation.warning] if navigation.warning else []
            navigation_links = _get_safe_navigation_links(
                page,
                website_url,
                execution_budget,
            )

            return SmokeTestExecution(
                results=[
                    _execute_case(
                        test_case,
                        page,
                        browser,
                        website_url,
                        console_errors,
                        network_errors,
                        navigation_notes,
                        navigation_links,
                        execution_budget,
                    )
                    for test_case in test_cases
                ],
                environment=environment,
            )
        finally:
            browser.close()


def _launch_browser(playwright, browser_engine: BrowserEngine) -> Browser:
    browser_type = getattr(playwright, browser_engine.value)
    try:
        return browser_type.launch(**browser_launch_options(browser_engine.value))
    except PlaywrightError as error:
        raise BrowserEngineUnavailableError(browser_engine) from error


def _create_execution_environment(
    browser: Browser,
    browser_engine: BrowserEngine,
) -> ExecutionEnvironment:
    return ExecutionEnvironment(
        browser_engine=browser_engine.display_name,
        browser_version=browser.version,
        operating_system=system(),
        viewport_width=DEFAULT_VIEWPORT["width"],
        viewport_height=DEFAULT_VIEWPORT["height"],
        playwright_version=version("playwright"),
    )


def _select_adaptive_test_cases(
    page: Page,
    test_cases: list[SmokeTestCase],
) -> list[SmokeTestCase]:
    selected_test_cases = list(test_cases)
    if _has_visible_form(page) and not any(
        test_case.test_case_id == "SMK-006" for test_case in selected_test_cases
    ):
        selected_test_cases.append(create_form_availability_test_case())

    if _visible_form_control_labels(page) and not any(
        test_case.test_case_id == "SMK-007" for test_case in selected_test_cases
    ):
        selected_test_cases.append(create_form_accessibility_test_case())
    return selected_test_cases


def _has_visible_form(page: Page) -> bool:
    return _visible_form_count(page) > 0


def _visible_form_count(page: Page) -> int:
    return page.locator("form:visible").count()


def _visible_form_control_labels(page: Page) -> list[bool]:
    return page.locator("form:visible").evaluate_all(
        """
        forms => forms.flatMap(form =>
          Array.from(form.querySelectorAll("input, select, textarea"))
            .filter(control => {
              const type = (control.getAttribute("type") || "").toLowerCase();
              if (["hidden", "submit", "button", "reset", "image"].includes(type)) {
                return false;
              }
              const style = window.getComputedStyle(control);
              const bounds = control.getBoundingClientRect();
              return style.display !== "none" && style.visibility !== "hidden"
                && bounds.width > 0 && bounds.height > 0;
            })
            .map(control => {
              const hasLabel = Array.from(control.labels || []).some(
                label => Boolean(label.textContent.trim())
              );
              const hasAriaLabel = Boolean((control.getAttribute("aria-label") || "").trim());
              const hasLabelledBy = (control.getAttribute("aria-labelledby") || "")
                .split(/\\s+/)
                .filter(Boolean)
                .some(id => Boolean(document.getElementById(id)?.textContent.trim()));
              const hasTitle = Boolean((control.getAttribute("title") || "").trim());
              return hasLabel || hasAriaLabel || hasLabelledBy || hasTitle;
            })
        )
        """
    )


def _execute_case(
    test_case: SmokeTestCase,
    page: Page,
    browser: Browser,
    website_url: str,
    console_errors: list[str],
    network_errors: list[str],
    navigation_notes: list[str],
    navigation_links: list[str],
    execution_budget: SmokeExecutionBudget,
) -> SmokeTestResult:
    started_at = perf_counter()
    passed, actual_result, notes = _evaluate_case(
        test_case.test_case_id,
        page,
        browser,
        website_url,
        navigation_links,
        execution_budget,
    )
    return SmokeTestResult(
        test_case_id=test_case.test_case_id,
        title=test_case.title,
        status="Passed" if passed else "Failed",
        actual_result=actual_result,
        duration_seconds=round(perf_counter() - started_at, 3),
        console_errors=list(console_errors),
        network_errors=list(network_errors),
        notes=[*navigation_notes, *notes],
    )


def _evaluate_case(
    test_case_id: str,
    page: Page,
    browser: Browser,
    website_url: str,
    navigation_links: list[str],
    execution_budget: SmokeExecutionBudget,
) -> tuple[bool, str, list[str]]:
    execution_budget.raise_if_expired()
    if test_case_id == "SMK-001":
        has_content = page.locator("body:visible").count() > 0
        has_title = bool(page.title().strip())
        passed = has_content and has_title
        if passed:
            return True, "Homepage has visible content and a title.", []
        missing_parts = []
        if not has_content:
            missing_parts.append("visible homepage content")
        if not has_title:
            missing_parts.append("a page title")
        return False, f"Homepage is missing {' and '.join(missing_parts)}.", []

    if test_case_id == "SMK-002":
        navigation_count = len(navigation_links)
        passed = navigation_count > 0
        return passed, f"Found {navigation_count} visible same-origin navigation links.", []

    if test_case_id == "SMK-003":
        return _check_navigation_links(browser, navigation_links, execution_budget)

    if test_case_id == "SMK-004":
        return _check_contact_link(page, browser, website_url, execution_budget)

    if test_case_id == "SMK-005":
        footer_containers = _get_visible_footer_containers(page)
        if footer_containers:
            return (
                True,
                f"Found visible footer container: {footer_containers[0]}.",
                [],
            )
        return False, "No visible footer container was found.", []

    if test_case_id == "SMK-006":
        form_count = _visible_form_count(page)
        return (
            form_count > 0,
            f"Found {form_count} visible form(s); no data was entered or submitted.",
            [],
        )

    if test_case_id == "SMK-007":
        control_labels = _visible_form_control_labels(page)
        if not control_labels:
            return False, "No visible form controls remained to inspect.", []
        unlabeled_count = sum(not has_label for has_label in control_labels)
        if unlabeled_count:
            return (
                False,
                f"Found {unlabeled_count} of {len(control_labels)} visible form control(s) without an accessible name.",
                [],
            )
        return (
            True,
            f"All {len(control_labels)} visible form control(s) have accessible names; no data was entered or submitted.",
            [],
        )

    return False, "No deterministic executor is defined for this test case.", [
        "Test case was not executed."
    ]


def _check_navigation_links(
    browser: Browser,
    navigation_links: list[str],
    execution_budget: SmokeExecutionBudget,
) -> tuple[bool, str, list[str]]:
    selected_links = navigation_links[:MAX_NAVIGATION_LINKS]
    if not selected_links:
        return False, "No safe same-origin navigation links were found.", []

    failed_links = [
        link
        for link in selected_links
        if not _page_loads(browser, link, execution_budget)
    ]
    if failed_links:
        return False, "One or more selected navigation links failed to load.", failed_links
    return True, f"Loaded {len(selected_links)} selected navigation links.", []


def _get_safe_navigation_links(
    page: Page,
    website_url: str,
    execution_budget: SmokeExecutionBudget,
) -> list[str]:
    navigation_locator = page.locator(NAVIGATION_CONTAINER_SELECTOR).locator(
        "a:visible"
    )
    try:
        navigation_locator.first.wait_for(
            state="visible",
            timeout=execution_budget.limit_wait_timeout_ms(
                NAVIGATION_SNAPSHOT_TIMEOUT_MS
            ),
        )
    except PlaywrightTimeoutError:
        execution_budget.raise_if_expired()
        return []

    links = navigation_locator.evaluate_all(
        "links => links.map(link => link.href)"
    )
    return [
        link for link in links if _is_safe_navigation_target(link, website_url)
    ]


def _get_visible_footer_containers(page: Page) -> list[str]:
    footer_candidates = page.locator(FOOTER_CONTAINER_SELECTOR).evaluate_all(
        """
        elements => elements.map(element => ({
            tagName: element.tagName.toLowerCase(),
            id: element.id,
            className: element.getAttribute('class') || ''
        }))
        """
    )
    return [_describe_container(candidate) for candidate in footer_candidates]


def _describe_container(candidate: dict[str, str]) -> str:
    if candidate["id"]:
        return f"#{candidate['id']}"
    if candidate["className"]:
        first_class = candidate["className"].split()[0]
        return f"{candidate['tagName']}.{first_class}"
    return f"<{candidate['tagName']}>"


def _check_contact_link(
    page: Page,
    browser,
    website_url: str,
    execution_budget: SmokeExecutionBudget,
) -> tuple[bool, str, list[str]]:
    links = page.locator("a:visible").evaluate_all(
        """
        links => links.map(link => ({
            text: link.innerText.trim(),
            url: link.href
        }))
        """
    )
    contact_links = [
        link
        for link in links
        if "contact" in f"{link['text']} {link['url']}".lower()
    ]
    if not contact_links:
        return False, "No contact link or section was found.", []

    contact_url = contact_links[0]["url"]
    if contact_url.startswith("#"):
        return True, "A contact section link is present on the homepage.", []
    if not _is_safe_navigation_target(contact_url, website_url):
        return False, "The contact link is outside the safe navigation scope.", [contact_url]
    if _page_loads(browser, contact_url, execution_budget):
        return True, "The contact page loaded successfully.", []
    return False, "The contact page did not load successfully.", [contact_url]


def _page_loads(
    browser: Browser,
    target_url: str,
    execution_budget: SmokeExecutionBudget,
) -> bool:
    target_page = browser.new_page()
    try:
        navigation = navigate_to_page(target_page, target_url, execution_budget)
        return navigation.loaded and (
            bool(target_page.title().strip())
            or target_page.locator("body:visible").count() > 0
        )
    finally:
        target_page.close()


def _is_safe_navigation_target(target_url: str, website_url: str) -> bool:
    target = urlparse(target_url)
    website = urlparse(website_url)
    path_terms = {
        term
        for segment in target.path.split("/")
        for term in re.split(r"[^a-z0-9]+", segment.lower())
        if term
    }
    return (
        target.scheme in {"http", "https"}
        and target.netloc == website.netloc
        and not path_terms.intersection(SENSITIVE_PATH_KEYWORDS)
    )


def _register_error_listeners(
    page: Page,
    console_errors: list[str],
    network_errors: list[str],
) -> None:
    def collect_console_error(message: ConsoleMessage) -> None:
        if message.type == "error" and len(console_errors) < MAX_ERRORS:
            console_errors.append(message.text)

    def collect_network_error(response: Response) -> None:
        if response.status >= 400 and len(network_errors) < MAX_ERRORS:
            network_errors.append(f"{response.status} {response.url}")

    page.on("console", collect_console_error)
    page.on("response", collect_network_error)


def _failed_navigation_result(
    test_case: SmokeTestCase,
    error_message: str,
    duration_seconds: float,
) -> SmokeTestResult:
    return SmokeTestResult(
        test_case_id=test_case.test_case_id,
        title=test_case.title,
        status="Failed",
        actual_result="Homepage could not be loaded.",
        duration_seconds=duration_seconds,
        console_errors=[],
        network_errors=[],
        notes=[error_message],
    )
