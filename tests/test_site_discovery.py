from app.services.site_discovery import discover_site


class FakeMessage:
    def __init__(self, message_type: str, text: str):
        self.type = message_type
        self.text = text


class FakeResponse:
    def __init__(self, status: int, url: str):
        self.status = status
        self.url = url


class FakeLocator:
    def __init__(self, selector: str):
        self.selector = selector

    def evaluate_all(self, _script: str):
        return [
            {"text": "Services", "url": "https://example.com/services"},
            {"text": "Contact", "url": "https://example.com/contact"},
        ]

    def all_inner_texts(self):
        return ["Example Business", "Reliable Services"]

    def count(self):
        return {"form": 1, "footer:visible": 1}[self.selector]


class FakePage:
    url = "https://example.com/"

    def __init__(self):
        self.handlers = {}
        self.goto_arguments = None

    def on(self, event: str, handler):
        self.handlers[event] = handler

    def goto(self, url: str, *, wait_until: str, timeout: int):
        self.goto_arguments = (url, wait_until, timeout)
        self.handlers["console"](FakeMessage("error", "Failed to load asset"))
        self.handlers["response"](FakeResponse(404, "https://example.com/missing"))

    def title(self):
        return "Example Business"

    def locator(self, selector: str):
        return FakeLocator(selector)


class FakeBrowser:
    def __init__(self):
        self.page = FakePage()
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self):
        self.browser = FakeBrowser()
        self.launch_arguments = None

    def launch(self, *, headless: bool, chromium_sandbox: bool):
        self.launch_arguments = {
            "headless": headless,
            "chromium_sandbox": chromium_sandbox,
        }
        return self.browser


class FakePlaywright:
    def __init__(self):
        self.chromium = FakeChromium()


class FakePlaywrightContext:
    def __init__(self):
        self.playwright = FakePlaywright()

    def __enter__(self):
        return self.playwright

    def __exit__(self, *_args):
        return False


def test_discover_site_collects_bounded_homepage_signals(monkeypatch):
    context = FakePlaywrightContext()
    monkeypatch.setattr(
        "app.services.site_discovery.sync_playwright",
        lambda: context,
    )
    monkeypatch.setattr(
        "app.services.navigation.validate_public_url",
        lambda url: url,
    )

    discovery = discover_site("https://example.com")

    assert discovery.website_url == "https://example.com/"
    assert discovery.page_title == "Example Business"
    assert discovery.detected_website_type == "Business Website"
    assert discovery.visible_links[0].text == "Services"
    assert discovery.headings == ["Example Business", "Reliable Services"]
    assert discovery.form_count == 1
    assert discovery.footer_present is True
    assert discovery.console_errors == ["Failed to load asset"]
    assert discovery.network_errors == ["404 https://example.com/missing"]
    assert discovery.navigation_warnings == []
    assert context.playwright.chromium.launch_arguments == {
        "headless": True,
        "chromium_sandbox": True,
    }
    assert context.playwright.chromium.browser.page.goto_arguments == (
        "https://example.com",
        "domcontentloaded",
        30_000,
    )
    assert context.playwright.chromium.browser.closed is True
