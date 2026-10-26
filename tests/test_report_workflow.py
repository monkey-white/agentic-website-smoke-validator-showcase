from datetime import UTC, datetime
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.browser_profile import BrowserEngine
from app.models.smoke_result import SmokeTestResult
from app.models.test_execution import ExecutionEnvironment, SmokeTestExecution
from app.services.report_workflow import create_report_filename
from app.services.smoke_executor import BrowserEngineUnavailableError
from app.services.smoke_execution_budget import SmokeExecutionTimeoutError
from app.services.request_rate_limiter import (
    InMemoryRequestRateLimiter,
    smoke_run_rate_limiter,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_smoke_run_rate_limiter():
    smoke_run_rate_limiter.reset()


def test_report_runner_renders_user_testable_page():
    response = client.get("/")

    assert response.status_code == 200
    assert "Website Smoke Validator" in response.text
    assert "/api/report" in response.text
    assert 'type="text"' in response.text
    assert 'id="execution-status"' in response.text
    assert "Smoke check in progress" in response.text
    assert "We do not store your test data" in response.text
    assert "Download the PDF if you want to keep it" in response.text
    assert 'href="mailto:support@agenticwebsitesmokevalidator.com"' in response.text
    assert "Test settings" in response.text
    assert '<option value="firefox">Firefox</option>' in response.text
    assert "Smoke check took too long to complete. Please try again." in response.text


def test_create_report_runs_existing_workflow_and_returns_html(monkeypatch):
    captured = {}

    def fake_execute(website_url, test_cases, browser_engine):
        captured["website_url"] = website_url
        captured["test_case_ids"] = [test_case.test_case_id for test_case in test_cases]
        captured["browser_engine"] = browser_engine
        return SmokeTestExecution(
            results=[
                SmokeTestResult(
                    test_case_id="SMK-001",
                    title="Verify homepage loads successfully",
                    status="Passed",
                    actual_result="Homepage loaded successfully.",
                    duration_seconds=0.1,
                    console_errors=[],
                    network_errors=[],
                    notes=[],
                )
            ],
            environment=ExecutionEnvironment(
                browser_engine="Chromium",
                browser_version="123.0.4567.0",
                operating_system="Linux",
                viewport_width=1280,
                viewport_height=720,
                playwright_version="1.61.0",
            ),
        )

    monkeypatch.setattr(
        "app.services.report_workflow.execute_smoke_test_plan",
        fake_execute,
    )
    monkeypatch.setattr(
        "app.services.report_workflow.validate_public_url",
        lambda website_url: "https://example.com",
    )
    monkeypatch.setattr(
        "app.services.report_workflow.analyze_diagnostics",
        lambda _results: [],
    )

    response = client.post(
        "/api/report",
        json={"website_url": "example.com", "browser_engine": "firefox"},
    )

    assert response.status_code == 200
    assert captured == {
        "website_url": "https://example.com",
        "test_case_ids": ["SMK-001", "SMK-002", "SMK-003", "SMK-004", "SMK-005"],
        "browser_engine": BrowserEngine.FIREFOX,
    }
    assert "Smoke Test Report" in response.text
    assert "https://example.com" in response.text
    assert "/api/report.pdf" in response.text
    assert "PDF download in progress" in response.text
    assert "Run another test" in response.text
    assert "Download and proceed" in response.text
    assert "Browser:</span> Chromium 123.0.4567.0" in response.text


def test_create_report_rejects_invalid_url():
    response = client.post("/api/report", json={"website_url": "ftp://example.com"})

    assert response.status_code == 400
    assert response.json() == {"detail": "URL must use http or https."}


def test_create_report_rejects_non_public_url(monkeypatch):
    monkeypatch.setattr(
        "app.services.report_workflow.validate_public_url",
        lambda _website_url: (_ for _ in ()).throw(
            ValueError("URL must resolve only to public addresses.")
        ),
    )

    response = client.post("/api/report", json={"website_url": "127.0.0.1"})

    assert response.status_code == 400
    assert response.json() == {
        "detail": "URL must resolve only to public addresses."
    }


def test_create_report_rejects_unknown_browser_engine():
    response = client.post(
        "/api/report",
        json={"website_url": "example.com", "browser_engine": "safari"},
    )

    assert response.status_code == 422


def test_create_report_reports_unavailable_browser_engine(monkeypatch):
    monkeypatch.setattr(
        "app.routes.report.create_smoke_report",
        lambda *_args: (_ for _ in ()).throw(
            BrowserEngineUnavailableError(BrowserEngine.WEBKIT)
        ),
    )

    response = client.post(
        "/api/report",
        json={"website_url": "example.com", "browser_engine": "webkit"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "WebKit is not available on this server."
    }


def test_create_report_reports_execution_timeout(monkeypatch):
    monkeypatch.setattr(
        "app.routes.report.create_smoke_report",
        lambda *_args: (_ for _ in ()).throw(SmokeExecutionTimeoutError()),
    )

    response = client.post("/api/report", json={"website_url": "example.com"})

    assert response.status_code == 504
    assert response.json() == {
        "detail": (
            "Smoke check exceeded the 240-second execution limit. Please try again."
        )
    }


def test_create_report_rejects_when_browser_capacity_is_exhausted(monkeypatch):
    @contextmanager
    def busy_browser_execution():
        from app.services.browser_capacity import BrowserExecutionBusyError

        raise BrowserExecutionBusyError
        yield

    monkeypatch.setattr(
        "app.routes.report.reserve_browser_execution",
        busy_browser_execution,
    )

    response = client.post("/api/report", json={"website_url": "example.com"})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    assert response.json() == {
        "detail": "Another browser task is already running. Please try again shortly."
    }


def test_create_report_rate_limits_repeated_smoke_runs(monkeypatch):
    monkeypatch.setattr(
        "app.routes.report.smoke_run_rate_limiter",
        InMemoryRequestRateLimiter(max_requests=10, window_seconds=3_600),
    )
    monkeypatch.setattr(
        "app.routes.report.create_smoke_report",
        lambda *_args: type("Report", (), {"report_html": "<html>Report</html>"})(),
    )

    for _ in range(10):
        assert client.post("/api/report", json={"website_url": "example.com"}).status_code == 200

    response = client.post("/api/report", json={"website_url": "example.com"})

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
    assert response.json() == {
        "detail": "Too many smoke checks from this address. Please try again later."
    }


def test_create_report_pdf_returns_download(monkeypatch):
    monkeypatch.setattr(
        "app.routes.report.render_report_pdf",
        lambda report_html: b"%PDF-1.4\n" + report_html.encode(),
    )
    monkeypatch.setattr(
        "app.routes.report.create_report_filename",
        lambda _website_url: "smoke-test-report-example-com-20260715T134500Z.pdf",
    )

    response = client.post(
        "/api/report.pdf",
        json={
            "website_url": "example.com",
            "report_html": "<html><body>Report</body></html>",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="smoke-test-report-example-com-20260715T134500Z.pdf"'
    )
    assert response.content.startswith(b"%PDF-1.4")


def test_create_report_pdf_rejects_empty_html():
    response = client.post(
        "/api/report.pdf",
        json={"website_url": "example.com", "report_html": "   "},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Report HTML is required."}


def test_create_report_filename_includes_hostname_and_timestamp():
    filename = create_report_filename(
        "https://www.example.com/path",
        generated_at=datetime(2026, 7, 15, 13, 45, tzinfo=UTC),
    )

    assert filename == "smoke-test-report-www-example-com-20260715T134500Z.pdf"
