from app.models.site_profile import SiteProfile


def create_default_site_profile(normalized_url: str) -> SiteProfile:
    return SiteProfile(
        website_url=normalized_url,
        detected_website_type="Business Website",
        detected_browser="Chromium",
        smoke_scope="Basic Business Website Smoke Validation",
        selected_test_count="5-10",
    )