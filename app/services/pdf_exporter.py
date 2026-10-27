from playwright.sync_api import sync_playwright
from app.services.browser_policy import browser_launch_options


def render_report_pdf(report_html: str) -> bytes:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options("chromium"))
        try:
            page = browser.new_page(java_script_enabled=False)
            page.route("**/*", lambda route: route.abort())
            page.set_content(report_html, wait_until="load")
            return page.pdf(
                format="A4",
                print_background=True,
                margin={
                    "top": "16mm",
                    "right": "12mm",
                    "bottom": "16mm",
                    "left": "12mm",
                },
            )
        finally:
            browser.close()
