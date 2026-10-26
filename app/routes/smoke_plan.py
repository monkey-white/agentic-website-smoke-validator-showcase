from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.smoke_plan import TestPlanResponse
from app.services.site_profiler import create_default_site_profile
from app.services.test_planner import create_default_smoke_test_plan
from app.services.url_validator import normalize_url


router = APIRouter(prefix="/api", tags=["test-plan"])


class TestPlanRequest(BaseModel):
    website_url: str


@router.post("/test-plan", response_model=TestPlanResponse)
def create_test_plan(request: TestPlanRequest) -> TestPlanResponse:
    try:
        normalized_url = normalize_url(request.website_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    site_profile = create_default_site_profile(normalized_url)
    tests = create_default_smoke_test_plan(site_profile)

    return TestPlanResponse(
        website_url=site_profile.website_url,
        test_count=len(tests),
        tests=tests,
    )
