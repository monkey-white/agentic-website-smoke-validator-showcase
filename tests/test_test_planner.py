from app.models.site_profile import SiteProfile
from app.services.test_planner import create_default_smoke_test_plan


def test_create_default_smoke_test_plan_returns_five_tests():
    site_profile = SiteProfile(
        website_url="https://example.com",
        detected_website_type="Business Website",
        detected_browser="Chromium",
        smoke_scope="Basic Business Website Smoke Validation",
        selected_test_count="5-10",
    )

    test_plan = create_default_smoke_test_plan(site_profile)

    assert len(test_plan) == 5


def test_create_default_smoke_test_plan_includes_homepage_test():
    site_profile = SiteProfile(
        website_url="https://example.com",
        detected_website_type="Business Website",
        detected_browser="Chromium",
        smoke_scope="Basic Business Website Smoke Validation",
        selected_test_count="5-10",
    )

    test_plan = create_default_smoke_test_plan(site_profile)

    assert test_plan[0].test_case_id == "SMK-001"
    assert test_plan[0].title == "Verify homepage loads successfully"
    assert test_plan[0].priority == "High"
    assert test_plan[0].automation_candidate is True