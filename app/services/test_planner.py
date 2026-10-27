from app.models.site_profile import SiteProfile
from app.models.test_case import SmokeTestCase


def create_form_availability_test_case() -> SmokeTestCase:
    return SmokeTestCase(
        test_case_id="SMK-006",
        title="Verify a visible form is available without submitting it",
        priority="Low",
        type="Smoke",
        preconditions=["At least one visible form is present on the homepage"],
        steps=[
            "Locate a visible form on the homepage",
            "Verify the form is present",
            "Do not enter data or submit the form",
        ],
        expected_result=(
            "At least one visible form is available; no data was entered or submitted."
        ),
        automation_candidate=True,
    )


def create_default_smoke_test_plan(site_profile: SiteProfile) -> list[SmokeTestCase]:
    return [
        SmokeTestCase(
            test_case_id="SMK-001",
            title="Verify homepage loads successfully",
            priority="High",
            type="Smoke",
            preconditions=[
                "Website is publicly accessible",
                f"Website URL is {site_profile.website_url}",
            ],
            steps=[
                "Navigate to the website URL",
                "Wait for the page to load",
                "Verify visible content is present",
                "Verify page title is present",
            ],
            expected_result="Homepage loads successfully with visible content and a valid title.",
            automation_candidate=True,
        ),
        SmokeTestCase(
            test_case_id="SMK-002",
            title="Verify primary navigation is visible",
            priority="High",
            type="Smoke",
            preconditions=[
                "Homepage loads successfully",
            ],
            steps=[
                "Open the homepage",
                "Identify the primary navigation area",
                "Verify navigation links are visible",
            ],
            expected_result="Primary navigation is visible and contains clickable links.",
            automation_candidate=True,
        ),
        SmokeTestCase(
            test_case_id="SMK-003",
            title="Verify main navigation links open successfully",
            priority="Medium",
            type="Smoke",
            preconditions=[
                "Primary navigation links are visible",
            ],
            steps=[
                "Open the homepage",
                "Identify key navigation links",
                "Open selected navigation links",
                "Verify each selected page loads successfully",
            ],
            expected_result="Selected navigation links open valid pages without critical errors.",
            automation_candidate=True,
        ),
        SmokeTestCase(
            test_case_id="SMK-004",
            title="Verify contact page or contact section is reachable",
            priority="Medium",
            type="Smoke",
            preconditions=[
                "Homepage loads successfully",
            ],
            steps=[
                "Open the homepage",
                "Locate a Contact link, button, or section",
                "Navigate to the contact page or section",
                "Verify contact-related content is visible",
            ],
            expected_result="A contact page, contact section, or contact information is reachable.",
            automation_candidate=True,
        ),
        SmokeTestCase(
            test_case_id="SMK-005",
            title="Verify footer content is visible",
            priority="Low",
            type="Smoke",
            preconditions=[
                "Homepage loads successfully",
            ],
            steps=[
                "Open the homepage",
                "Scroll to the footer",
                "Verify footer content or footer links are visible",
            ],
            expected_result="Footer information is visible and contains business-relevant content.",
            automation_candidate=True,
        ),
    ]
