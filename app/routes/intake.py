from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.site_profile import SiteProfile
from app.services.site_profiler import create_default_site_profile
from app.services.url_validator import normalize_url


router = APIRouter(prefix="/api", tags=["intake"])


class IntakeRequest(BaseModel):
    website_url: str


@router.post("/intake", response_model=SiteProfile)
def create_intake(request: IntakeRequest):
    try:
        normalized_url = normalize_url(request.website_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return create_default_site_profile(normalized_url)