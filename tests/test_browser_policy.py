import pytest

from app.services.browser_policy import browser_launch_options


def test_local_browser_options_keep_chromium_sandbox_enabled(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("VALIDATOR_HTTP_PROXY", raising=False)

    assert browser_launch_options("chromium") == {
        "headless": True,
        "chromium_sandbox": True,
    }


def test_proxy_is_used_by_every_engine_and_chromium_disables_loopback_bypass(monkeypatch):
    monkeypatch.setenv("VALIDATOR_HTTP_PROXY", "http://egress:3128")

    assert browser_launch_options("chromium") == {
        "headless": True,
        "proxy": {"server": "http://egress:3128", "bypass": "<-loopback>"},
        "chromium_sandbox": True,
    }
    assert browser_launch_options("firefox") == {
        "headless": True,
        "proxy": {"server": "http://egress:3128"},
    }


def test_production_requires_egress_proxy(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("VALIDATOR_HTTP_PROXY", raising=False)

    with pytest.raises(RuntimeError, match="VALIDATOR_HTTP_PROXY is required"):
        browser_launch_options("chromium")
