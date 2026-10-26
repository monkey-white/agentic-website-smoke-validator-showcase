from playwright.sync_api import ConsoleMessage, Page, Response, sync_playwright

from app.models.site_discovery import DiscoveredLink, SiteDiscovery
from app.services.navigation import navigate_to_page


MAX_VISIBLE_LINKS = 20
MAX_HEADINGS = 20
MAX_ERRORS = 20
BUSINESS_KEYWORDS = {
    "about",
    "company",
    "contact",
    "location",
    "products",
    "services",
    "team",
}


def discover_site(website_url: str) -> SiteDiscovery:
    console_errors: list[str] = []
    network_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            chromium_sandbox=True,
        )
        try:
            page = browser.new_page()
            _register_error_listeners(page, console_errors, network_errors)
            navigation = navigate_to_page(page, website_url)
            if not navigation.loaded:
                raise RuntimeError(f"Homepage could not be loaded: {navigation.error}")

            visible_links = _collect_visible_links(page)
            headings = _collect_headings(page)

            return SiteDiscovery(
                website_url=page.url,
                page_title=page.title(),
                detected_website_type=_classify_website(visible_links, headings),
                visible_links=visible_links,
                headings=headings,
                form_count=page.locator("form").count(),
                footer_present=page.locator("footer:visible").count() > 0,
                console_errors=console_errors,
                network_errors=network_errors,
                navigation_warnings=[navigation.warning]
                if navigation.warning
                else [],
            )
        finally:
            browser.close()


def _register_error_listeners(
    page: Page,
    console_errors: list[str],
    network_errors: list[str],
) -> None:
    def collect_console_error(message: ConsoleMessage) -> None:
        if message.type == "error":
            _append_bounded(console_errors, message.text)

    def collect_network_error(response: Response) -> None:
        if response.status >= 400:
            _append_bounded(network_errors, f"{response.status} {response.url}")

    page.on("console", collect_console_error)
    page.on("response", collect_network_error)


def _collect_visible_links(page: Page) -> list[DiscoveredLink]:
    raw_links = page.locator("a:visible").evaluate_all(
        """
        links => links.map(link => ({
            text: link.innerText.trim(),
            url: link.href
        })).filter(link => link.text || link.url)
        """
    )
    return [
        DiscoveredLink.model_validate(link)
        for link in raw_links[:MAX_VISIBLE_LINKS]
    ]


def _collect_headings(page: Page) -> list[str]:
    headings = page.locator("h1:visible, h2:visible, h3:visible").all_inner_texts()
    return [heading.strip() for heading in headings if heading.strip()][
        :MAX_HEADINGS
    ]


def _classify_website(
    visible_links: list[DiscoveredLink],
    headings: list[str],
) -> str:
    visible_text = " ".join(
        [link.text for link in visible_links] + headings
    ).lower()
    if any(keyword in visible_text for keyword in BUSINESS_KEYWORDS):
        return "Business Website"
    return "Unknown"


def _append_bounded(messages: list[str], message: str) -> None:
    if len(messages) < MAX_ERRORS:
        messages.append(message)
