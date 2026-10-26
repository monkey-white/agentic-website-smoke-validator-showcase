from enum import StrEnum


class BrowserEngine(StrEnum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"

    @property
    def display_name(self) -> str:
        return {
            BrowserEngine.CHROMIUM: "Chromium",
            BrowserEngine.FIREFOX: "Firefox",
            BrowserEngine.WEBKIT: "WebKit",
        }[self]
