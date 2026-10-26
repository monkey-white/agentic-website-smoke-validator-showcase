from dataclasses import dataclass
from datetime import UTC, datetime
import re
from urllib.parse import urlparse

from app.models.browser_profile import BrowserEngine
from app.services.diagnostic_analyzer import analyze_diagnostics
from app.services.report_renderer import render_smoke_report
from app.services.site_profiler import create_default_site_profile
from app.services.smoke_executor import execute_smoke_test_plan
from app.services.test_planner import create_default_smoke_test_plan
from app.services.url_validator import normalize_url, validate_public_url


@dataclass(frozen=True)
class GeneratedReport:
    report_html: str
    pdf_filename: str


def create_smoke_report(
    website_url: str,
    browser_engine: BrowserEngine = BrowserEngine.CHROMIUM,
) -> GeneratedReport:
    normalized_url = validate_public_url(website_url)
    site_profile = create_default_site_profile(normalized_url)
    test_cases = create_default_smoke_test_plan(site_profile)
    execution = execute_smoke_test_plan(
        normalized_url,
        test_cases,
        browser_engine,
    )
    diagnostic_analyses = analyze_diagnostics(execution.results)
    return GeneratedReport(
        report_html=render_smoke_report(
            normalized_url,
            execution.results,
            execution.environment,
            diagnostic_analyses,
            pdf_url="/api/report.pdf",
        ),
        pdf_filename=create_report_filename(normalized_url),
    )


def create_report_filename(
    website_url: str,
    generated_at: datetime | None = None,
) -> str:
    hostname = urlparse(normalize_url(website_url)).hostname or "website"
    safe_hostname = re.sub(r"[^a-z0-9]+", "-", hostname.lower()).strip("-")
    timestamp = (generated_at or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"smoke-test-report-{safe_hostname}-{timestamp}.pdf"
from datetime import UTC, datetime
import re
from urllib.parse import urlparse
