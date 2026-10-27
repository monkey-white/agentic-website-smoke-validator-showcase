from app.models.site_profile import SiteProfile
from app.services.test_planner import (
    create_default_smoke_test_plan,
    create_form_accessibility_test_case,
    create_form_availability_test_case,
    create_image_accessibility_test_case,
    create_link_accessibility_test_case,
)


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


def test_create_form_availability_test_is_read_only():
    test_case = create_form_availability_test_case()

    assert test_case.test_case_id == "SMK-006"
    assert test_case.automation_candidate is True
    assert "Do not enter data or submit the form" in test_case.steps
    assert "no data was entered or submitted" in test_case.expected_result


def test_create_form_accessibility_test_is_read_only():
    test_case = create_form_accessibility_test_case()

    assert test_case.test_case_id == "SMK-007"
    assert test_case.type == "Accessibility"
    assert test_case.automation_candidate is True
    assert "Do not focus, enter data, or submit any control" in test_case.steps


def test_create_image_accessibility_test_is_read_only():
    test_case = create_image_accessibility_test_case()

    assert test_case.test_case_id == "SMK-008"
    assert test_case.type == "Accessibility"
    assert test_case.automation_candidate is True
    assert "Do not click or otherwise interact with the images" in test_case.steps


def test_create_link_accessibility_test_is_read_only():
    test_case = create_link_accessibility_test_case()

    assert test_case.test_case_id == "SMK-009"
    assert test_case.type == "Accessibility"
    assert test_case.automation_candidate is True
    assert "Do not follow or activate any link" in test_case.steps
