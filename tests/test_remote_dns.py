import pytest

from app.services import remote_dns


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size: int) -> bytes:
        return self.payload


def test_resolve_remote_uses_only_fixed_internal_resolver(monkeypatch):
    monkeypatch.setenv("VALIDATOR_DNS_URL", "http://resolver:8053")
    calls = []
    monkeypatch.setattr(
        remote_dns,
        "build_opener",
        lambda handler: type(
            "Opener",
            (),
            {"open": lambda _self, request, timeout: (calls.append((request, timeout))
                or FakeResponse(b'{"addresses":["93.184.216.34"]}'))},
        )(),
    )

    assert remote_dns.resolve_remote("example.com") == {"93.184.216.34"}
    assert calls[0][0].full_url == "http://resolver:8053/resolve?host=example.com"
    assert calls[0][1] == 3


def test_resolve_remote_fails_closed_for_unapproved_endpoint(monkeypatch):
    monkeypatch.setenv("VALIDATOR_DNS_URL", "http://other:8053")

    with pytest.raises(ValueError, match="could not be resolved"):
        remote_dns.resolve_remote("example.com")


def test_resolve_remote_rejects_empty_or_malformed_address_result(monkeypatch):
    monkeypatch.setenv("VALIDATOR_DNS_URL", "http://resolver:8053")
    monkeypatch.setattr(
        remote_dns,
        "build_opener",
        lambda *_args: type(
            "Opener",
            (),
            {"open": lambda *_args, **_kwargs: FakeResponse(b'{"addresses":[]}')},
        )(),
    )

    with pytest.raises(ValueError, match="could not be resolved"):
        remote_dns.resolve_remote("example.com")
