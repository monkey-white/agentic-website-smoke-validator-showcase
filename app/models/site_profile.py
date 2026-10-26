from pydantic import BaseModel


class SiteProfile(BaseModel):
    website_url: str
    detected_website_type: str
    detected_browser: str
    smoke_scope: str
    selected_test_count: str