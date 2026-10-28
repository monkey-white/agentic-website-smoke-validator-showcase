from app.services.site_profiler import create_default_site_profile


def test_create_default_site_profile_returns_expected_defaults():
    profile = create_default_site_profile("https://example.com")

    assert profile.website_url == "https://example.com"
    assert profile.detected_website_type == "Business Website"
    assert profile.detected_browser == "Chromium"
    assert profile.smoke_scope == "Basic Business Website Smoke Validation"
    assert profile.selected_test_count == "20"
