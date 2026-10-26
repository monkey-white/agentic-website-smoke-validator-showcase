from app.services.pdf_exporter import render_report_pdf


class FakePage:
    def __init__(self):
        self.report_html = None
        self.set_content_arguments = None
        self.pdf_arguments = None

    def set_content(self, report_html: str, *, wait_until: str):
        self.report_html = report_html
        self.set_content_arguments = {"wait_until": wait_until}

    def route(self, url: str, handler):
        assert url == "**/*"

    def pdf(self, **arguments):
        self.pdf_arguments = arguments
        return b"%PDF-1.4\n"


class FakeBrowser:
    def __init__(self):
        self.page = FakePage()
        self.closed = False

    def new_page(self, *, java_script_enabled: bool):
        assert java_script_enabled is False
        return self.page

    def close(self):
        self.closed = True


class FakePlaywright:
    def __init__(self):
        self.browser = FakeBrowser()
        self.chromium = self

    def launch(self, *, headless: bool, chromium_sandbox: bool):
        assert headless is True
        assert chromium_sandbox is True
        return self.browser


class FakePlaywrightContext:
    def __init__(self):
        self.playwright = FakePlaywright()

    def __enter__(self):
        return self.playwright

    def __exit__(self, *_arguments):
        return False


def test_render_report_pdf_prints_existing_html(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.pdf_exporter.sync_playwright",
        lambda: context,
    )

    pdf = render_report_pdf("<html><body>Report</body></html>")

    assert pdf.startswith(b"%PDF-1.4")
    assert context.playwright.browser.page.report_html == "<html><body>Report</body></html>"
    assert context.playwright.browser.page.set_content_arguments == {"wait_until": "load"}
    assert context.playwright.browser.page.pdf_arguments == {
        "format": "A4",
        "print_background": True,
        "margin": {
            "top": "16mm",
            "right": "12mm",
            "bottom": "16mm",
            "left": "12mm",
        },
    }
    assert context.playwright.browser.closed is True
