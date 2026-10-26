from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check_returns_unknown_build_when_not_configured(monkeypatch):
    monkeypatch.delenv("APP_REPOSITORY", raising=False)
    monkeypatch.delenv("APP_COMMIT_SHA", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "repository": "unknown",
        "commit": "unknown",
    }
    assert response.headers["content-security-policy"] == (
        "default-src 'self'; "
        "base-uri 'self'; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'"
    )
    assert response.headers["permissions-policy"] == (
        "camera=(), geolocation=(), microphone=()"
    )
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_health_check_reports_configured_repository_and_commit(monkeypatch):
    monkeypatch.setenv(
        "APP_REPOSITORY",
        "monkey-white/agentic-website-smoke-validator-showcase",
    )
    monkeypatch.setenv("APP_COMMIT_SHA", "a1b2c3d4e5f6")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "repository": "monkey-white/agentic-website-smoke-validator-showcase",
        "commit": "a1b2c3d4e5f6",
    }
