from app.services import navigation
from app.services.navigation import navigate_to_page


class FakeTimeoutError(Exception):
    pass


class FakeLocator:
    def __init__(self, visible_count: int):
        self.visible_count = visible_count

    def count(self):
        return self.visible_count


class FakePage:
    def __init__(self, visible_body_count: int, error: Exception | None = None):
        self.visible_body_count = visible_body_count
        self.error = error
        self.goto_arguments = None
        self.url = "https://example.com"

    def goto(self, url: str, *, wait_until: str, timeout: int):
        self.goto_arguments = (url, wait_until, timeout)
        if self.error:
            raise self.error

    def locator(self, selector: str):
        assert selector == "body:visible"
        return FakeLocator(self.visible_body_count)


def test_navigation_uses_visible_content_after_timeout(monkeypatch):
    monkeypatch.setattr(navigation, "PlaywrightTimeoutError", FakeTimeoutError)
    monkeypatch.setattr(navigation, "validate_public_url", lambda url: url)
    page = FakePage(visible_body_count=1, error=FakeTimeoutError("Timed out"))

    result = navigate_to_page(page, "https://example.com")

    assert result.loaded is True
    assert result.warning == (
        "Page navigation exceeded the DOMContentLoaded timeout, "
        "but visible page content was available."
    )
    assert result.error is None
    assert page.goto_arguments == (
        "https://example.com",
        "domcontentloaded",
        30_000,
    )


def test_navigation_fails_when_timeout_has_no_visible_content(monkeypatch):
    monkeypatch.setattr(navigation, "PlaywrightTimeoutError", FakeTimeoutError)
    monkeypatch.setattr(navigation, "validate_public_url", lambda url: url)
    page = FakePage(visible_body_count=0, error=FakeTimeoutError("Timed out"))

    result = navigate_to_page(page, "https://example.com")

    assert result.loaded is False
    assert result.warning is None
    assert result.error == "Timed out"
    assert result.duration_seconds >= 0


def test_navigation_rejects_non_public_url_before_browser_navigation(monkeypatch):
    page = FakePage(visible_body_count=0)
    monkeypatch.setattr(
        navigation,
        "validate_public_url",
        lambda _url: (_ for _ in ()).throw(ValueError("URL must resolve only to public addresses.")),
    )

    result = navigate_to_page(page, "http://127.0.0.1")

    assert result.loaded is False
    assert result.error == "URL must resolve only to public addresses."
    assert page.goto_arguments is None


def test_navigation_rejects_blocked_redirect_destination(monkeypatch):
    page = FakePage(visible_body_count=1)
    page.url = "http://127.0.0.1"
    monkeypatch.setattr(
        navigation,
        "validate_public_url",
        lambda url: (
            (_ for _ in ()).throw(ValueError("URL must resolve only to public addresses."))
            if url == page.url
            else url
        ),
    )

    result = navigate_to_page(page, "https://example.com")

    assert result.loaded is False
    assert result.error == (
        "Navigation reached a blocked destination: "
        "URL must resolve only to public addresses."
    )
