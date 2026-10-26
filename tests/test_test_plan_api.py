from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_test_plan_returns_normalized_url_and_default_smoke_tests():
    response = client.post(
        "/api/test-plan",
        json={"website_url": "example.com"},
    )

    assert response.status_code == 200
    response_body = response.json()
    assert response_body["website_url"] == "https://example.com"
    assert response_body["test_count"] == 5
    assert [test["test_case_id"] for test in response_body["tests"]] == [
        "SMK-001",
        "SMK-002",
        "SMK-003",
        "SMK-004",
        "SMK-005",
    ]


def test_test_plan_rejects_invalid_url():
    response = client.post(
        "/api/test-plan",
        json={"website_url": "ftp://example.com"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "URL must use http or https.",
    }
