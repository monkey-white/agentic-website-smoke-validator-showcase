from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.smoke_result import SmokeTestResult
from app.models.diagnostic_analysis import DiagnosticAnalysis, DiagnosticKind
from app.models.test_execution import ExecutionEnvironment


TEMPLATE_DIRECTORY = Path(__file__).resolve().parent.parent / "templates"


def render_smoke_report(
    website_url: str,
    results: list[SmokeTestResult],
    environment: ExecutionEnvironment,
    diagnostic_analyses: list[DiagnosticAnalysis] | None = None,
    pdf_url: str | None = None,
) -> str:
    passed_count = sum(result.status == "Passed" for result in results)
    failed_count = sum(result.status == "Failed" for result in results)
    skipped_count = sum(result.status == "Skipped" for result in results)
    display_results = _deduplicate_diagnostics(results)
    warning_count = len(
        {
            (kind, message)
            for result in results
            for kind, messages in (
                ("console", result.console_errors),
                ("network", result.network_errors),
            )
            for message in messages
        }
    )

    if failed_count:
        overall_status = "Failed"
    elif warning_count:
        overall_status = "Passed with warnings"
    else:
        overall_status = "Passed"

    template = _create_environment().get_template("smoke_report.html")
    return template.render(
        website_url=website_url,
        environment=environment,
        results=display_results,
        diagnostic_analyses=_analysis_by_diagnostic(diagnostic_analyses or []),
        pdf_url=pdf_url,
        total_tests=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        warning_count=warning_count,
        overall_status=overall_status,
    )


def _create_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIRECTORY),
        autoescape=select_autoescape(["html"]),
    )


def _deduplicate_diagnostics(
    results: list[SmokeTestResult],
) -> list[SmokeTestResult]:
    seen_diagnostics: set[tuple[str, str]] = set()
    display_results: list[SmokeTestResult] = []
    for result in results:
        console_errors = _new_messages(
            "console", result.console_errors, seen_diagnostics
        )
        network_errors = _new_messages(
            "network", result.network_errors, seen_diagnostics
        )
        notes = _new_messages("note", result.notes, seen_diagnostics)
        display_results.append(
            result.model_copy(
                update={
                    "console_errors": console_errors,
                    "network_errors": network_errors,
                    "notes": notes,
                }
            )
        )
    return display_results


def _new_messages(
    kind: str,
    messages: list[str],
    seen_diagnostics: set[tuple[str, str]],
) -> list[str]:
    unique_messages: list[str] = []
    for message in messages:
        diagnostic = (kind, message)
        if diagnostic not in seen_diagnostics:
            seen_diagnostics.add(diagnostic)
            unique_messages.append(message)
    return unique_messages


def _analysis_by_diagnostic(
    diagnostic_analyses: list[DiagnosticAnalysis],
) -> dict[tuple[str, str], DiagnosticAnalysis]:
    return {
        (analysis.kind.value, analysis.message): analysis
        for analysis in diagnostic_analyses
    }
