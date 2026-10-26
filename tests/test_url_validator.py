import pytest

from app.services import url_validator
from app.services.url_validator import normalize_url, validate_public_url


def test_normalize_url_keeps_valid_https_url():
    result = normalize_url("https://example.com")

    assert result == "https://example.com"


def test_normalize_url_adds_https_when_scheme_is_missing():
    result = normalize_url("example.com")

    assert result == "https://example.com"


def test_normalize_url_trims_spaces():
    result = normalize_url("  https://example.com  ")

    assert result == "https://example.com"


def test_normalize_url_removes_trailing_slash():
    result = normalize_url("https://example.com/")

    assert result == "https://example.com"


def test_normalize_url_rejects_empty_value():
    with pytest.raises(ValueError, match="URL is required."):
        normalize_url("")


def test_normalize_url_rejects_non_http_scheme():
    with pytest.raises(ValueError, match="URL must use http or https."):
        normalize_url("ftp://example.com")


def test_normalize_url_rejects_missing_domain():
    with pytest.raises(ValueError, match="URL must include a valid domain."):
        normalize_url("https://")


def test_validate_public_url_accepts_public_host(monkeypatch):
    monkeypatch.setattr(
        url_validator.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 0))],
    )

    result = validate_public_url("https://example.com")

    assert result == "https://example.com"


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "::1"])
def test_validate_public_url_rejects_non_public_address(monkeypatch, address):
    monkeypatch.setattr(
        url_validator.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, (address, 0))],
    )

    with pytest.raises(ValueError, match="public addresses"):
        validate_public_url("https://example.com")


def test_validate_public_url_rejects_credentials():
    with pytest.raises(ValueError, match="must not include credentials"):
        validate_public_url("https://user:password@example.com")


def test_validate_public_url_rejects_non_standard_port():
    with pytest.raises(ValueError, match="standard HTTP or HTTPS port"):
        validate_public_url("https://example.com:8080")
