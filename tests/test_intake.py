from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_intake_normalizes_website_url():
    response = client.post(
        "/api/intake",
        json={"website_url": "example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "website_url": "https://example.com",
        "detected_website_type": "Business Website",
        "detected_browser": "Chromium",
        "smoke_scope": "Basic Business Website Smoke Validation",
        "selected_test_count": "5-10",
    }


def test_intake_rejects_invalid_url():
    response = client.post(
        "/api/intake",
        json={"website_url": "ftp://example.com"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "URL must use http or https.",
    }