from app.models.smoke_result import SmokeTestResult
from app.models.diagnostic_analysis import DiagnosticAnalysis, DiagnosticKind
from app.models.test_execution import ExecutionEnvironment
from app.services.report_renderer import render_smoke_report


EXECUTION_ENVIRONMENT = ExecutionEnvironment(
    browser_engine="Chromium",
    browser_version="123.0.4567.0",
    operating_system="Linux",
    viewport_width=1280,
    viewport_height=720,
    playwright_version="1.61.0",
)


def test_render_smoke_report_includes_summary_results_and_diagnostics():
    html = render_smoke_report(
        "https://example.com",
        [
            SmokeTestResult(
                test_case_id="SMK-001",
                title="Verify homepage loads successfully",
                status="Passed",
                actual_result="Homepage loaded successfully.",
                duration_seconds=0.123,
                console_errors=[],
                network_errors=[],
                notes=[],
            ),
            SmokeTestResult(
                test_case_id="SMK-002",
                title="Verify navigation is visible",
                status="Failed",
                actual_result="Navigation was not visible.",
                duration_seconds=0.456,
                console_errors=["<script>alert('error')</script>"],
                network_errors=["404 https://example.com/missing"],
                notes=["Review the navigation markup."],
            ),
        ],
        EXECUTION_ENVIRONMENT,
    )

    assert "Smoke Test Report" in html
    assert "https://example.com" in html
    assert "Overall Status" in html
    assert "Browser:</span> Chromium 123.0.4567.0" in html
    assert "Operating system:</span> Linux" in html
    assert "Viewport:</span> 1280 x 720" in html
    assert "Playwright:</span> 1.61.0" in html
    assert "Failed" in html
    assert "Total Tests" in html
    assert "<th>Test ID</th>" in html
    assert '<td class="test-id">SMK-001</td>' in html
    assert "SMK-001" in html
    assert "SMK-002" in html
    assert "0.123s" in html
    assert "Console: &lt;script&gt;alert(&#39;error&#39;)&lt;/script&gt;" in html
    assert "Network: 404 https://example.com/missing" in html
    assert "Note: Review the navigation markup." in html


def test_render_smoke_report_deduplicates_warning_diagnostics():
    duplicate_error = "requestStorageAccess: Permission denied."
    results = [
        SmokeTestResult(
            test_case_id=f"SMK-00{index}",
            title=f"Test {index}",
            status="Passed",
            actual_result="Passed.",
            duration_seconds=0.1,
            console_errors=[duplicate_error],
            network_errors=[],
            notes=[],
        )
        for index in (1, 2)
    ]

    html = render_smoke_report(
        "https://example.com", results, EXECUTION_ENVIRONMENT
    )

    assert html.count(f"Console: {duplicate_error}") == 1
    assert 'data-warning-count="1"' in html


def test_render_smoke_report_displays_ai_analysis_beside_raw_evidence():
    diagnostic = "requestStorageAccess: Permission denied."
    html = render_smoke_report(
        "https://example.com",
        [
            SmokeTestResult(
                test_case_id="SMK-001",
                title="Test 1",
                status="Passed",
                actual_result="Passed.",
                duration_seconds=0.1,
                console_errors=[diagnostic],
                network_errors=[],
                notes=[],
            )
        ],
        EXECUTION_ENVIRONMENT,
        [
            DiagnosticAnalysis(
                kind=DiagnosticKind.CONSOLE,
                message=diagnostic,
                explanation="The embedded content was denied permission.",
                likely_impact="May affect embedded login flows.",
                recommended_follow_up="Review the embedded content settings.",
            )
        ],
    )

    assert f"Console: {diagnostic}" in html
    assert "AI interpretation:" in html
    assert "The embedded content was denied permission." in html


def test_render_smoke_report_labels_related_warning_analysis():
    diagnostic = 'Cookie "_ga" has been rejected for invalid domain.'
    related_diagnostic = 'Cookie "_fbp" has been rejected for invalid domain.'
    html = render_smoke_report(
        "https://example.com",
        [
            SmokeTestResult(
                test_case_id="SMK-001",
                title="Test 1",
                status="Passed",
                actual_result="Passed.",
                duration_seconds=0.1,
                console_errors=[diagnostic, related_diagnostic],
                network_errors=[],
                notes=[],
            )
        ],
        EXECUTION_ENVIRONMENT,
        [
            DiagnosticAnalysis(
                kind=DiagnosticKind.CONSOLE,
                message=related_diagnostic,
                related_message_count=3,
                related_messages=[diagnostic, related_diagnostic],
                explanation="Three related cookies were rejected.",
                likely_impact="May affect analytics only.",
                recommended_follow_up="Review cookie domain settings.",
            )
        ],
    )

    assert "AI interpretation of 3 related warnings:" in html
    assert "Included in the 3 related-warning interpretation above." not in html
