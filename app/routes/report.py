from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.models.browser_profile import BrowserEngine
from app.services.browser_capacity import (
    BrowserExecutionBusyError,
    reserve_browser_execution,
)
from app.services.pdf_exporter import render_report_pdf
from app.services.request_rate_limiter import (
    RequestRateLimitError,
    smoke_run_rate_limiter,
)
from app.services.report_workflow import create_report_filename, create_smoke_report
from app.services.smoke_execution_budget import SmokeExecutionTimeoutError
from app.services.smoke_executor import BrowserEngineUnavailableError


router = APIRouter(tags=["reports"])
templates = Jinja2Templates(directory="app/templates")


class ReportRequest(BaseModel):
    website_url: str
    browser_engine: BrowserEngine = BrowserEngine.CHROMIUM


class PdfRequest(BaseModel):
    website_url: str
    report_html: str


@router.get("/", response_class=HTMLResponse)
def report_runner(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "report_runner.html")


@router.post("/api/report", response_class=HTMLResponse)
def create_report(
    report_request: ReportRequest,
    request: Request,
) -> HTMLResponse:
    try:
        smoke_run_rate_limiter.enforce(
            request.client.host if request.client else "unknown"
        )
        with reserve_browser_execution():
            report = create_smoke_report(
                report_request.website_url,
                report_request.browser_engine,
            )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except BrowserExecutionBusyError as error:
        raise HTTPException(
            status_code=429,
            detail="Another browser task is already running. Please try again shortly.",
            headers={"Retry-After": "30"},
        ) from error
    except RequestRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many smoke checks from this address. Please try again later.",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except BrowserEngineUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SmokeExecutionTimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error)) from error

    return HTMLResponse(report.report_html)


@router.post("/api/report.pdf")
def create_report_pdf(request: PdfRequest) -> Response:
    if not request.report_html.strip():
        raise HTTPException(status_code=400, detail="Report HTML is required.")
    if len(request.report_html) > 1_000_000:
        raise HTTPException(status_code=413, detail="Report HTML is too large.")
    try:
        pdf_filename = create_report_filename(request.website_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        with reserve_browser_execution():
            pdf_content = render_report_pdf(request.report_html)
    except BrowserExecutionBusyError as error:
        raise HTTPException(
            status_code=429,
            detail="Another browser task is already running. Please try again shortly.",
            headers={"Retry-After": "30"},
        ) from error

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{pdf_filename}"'
            ),
        },
    )
