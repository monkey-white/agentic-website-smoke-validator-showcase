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


def create_form_accessibility_test_case() -> SmokeTestCase:
    return SmokeTestCase(
        test_case_id="SMK-007",
        title="Verify visible form controls have accessible names",
        priority="Medium",
        type="Accessibility",
        preconditions=["At least one visible form control is present on the homepage"],
        steps=[
            "Inspect visible input, select, and text area controls",
            "Check for an associated label or accessible name",
            "Do not focus, enter data, or submit any control",
        ],
        expected_result=(
            "Every visible form control has an accessible name; no data was entered or submitted."
        ),
        automation_candidate=True,
    )


def create_image_accessibility_test_case() -> SmokeTestCase:
    return SmokeTestCase(
        test_case_id="SMK-008",
        title="Verify visible images have text alternatives or are decorative",
        priority="Medium",
        type="Accessibility",
        preconditions=["At least one visible image is present on the homepage"],
        steps=[
            "Inspect visible image elements for alternative text",
            "Accept empty alternative text or explicit decorative markup",
            "Do not click or otherwise interact with the images",
        ],
        expected_result=(
            "Every visible image has alternative text or is explicitly decorative."
        ),
        automation_candidate=True,
    )


def create_link_accessibility_test_case() -> SmokeTestCase:
    return SmokeTestCase(
        test_case_id="SMK-009",
        title="Verify visible links have accessible names",
        priority="Medium",
        type="Accessibility",
        preconditions=["At least one visible link is present on the homepage"],
        steps=[
            "Inspect visible links for text or an accessible name",
            "Include text alternatives from linked images",
            "Do not follow or activate any link",
        ],
        expected_result="Every visible link has an accessible name.",
        automation_candidate=True,
    )


def create_default_smoke_test_plan(site_profile: SiteProfile) -> list[SmokeTestCase]:
    test_cases = [
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

    test_cases.extend(
        [
            create_form_availability_test_case(),
            create_form_accessibility_test_case(),
            create_image_accessibility_test_case(),
            create_link_accessibility_test_case(),
        ]
    )
    test_cases.extend(
        [
            _create_basic_test_case(
                "SMK-010",
                "Verify the document language is declared",
                ["Inspect the root HTML element for a non-empty language value"],
                "The root HTML element declares a language.",
            ),
            _create_basic_test_case(
                "SMK-011",
                "Verify responsive viewport metadata is configured",
                ["Inspect the viewport meta element"],
                "The viewport metadata includes width=device-width.",
            ),
            _create_basic_test_case(
                "SMK-012",
                "Verify a main content landmark is present",
                ["Inspect the visible page for a main landmark"],
                "A visible main element or main landmark is present.",
            ),
            _create_basic_test_case(
                "SMK-013",
                "Verify the page has one primary heading",
                ["Count visible level-one headings"],
                "Exactly one visible level-one heading is present.",
            ),
            _create_basic_test_case(
                "SMK-014",
                "Verify heading levels do not skip",
                ["Inspect visible headings in document order"],
                "Visible heading levels progress without skipping a level.",
            ),
            _create_basic_test_case(
                "SMK-015",
                "Verify visible images have loaded",
                ["Check visible image elements for completed successful loads"],
                "Every visible image has loaded successfully.",
            ),
            _create_basic_test_case(
                "SMK-016",
                "Verify visible buttons have accessible names",
                ["Inspect visible buttons for text or an accessible name"],
                "Every visible button has an accessible name.",
            ),
            _create_basic_test_case(
                "SMK-017",
                "Verify page content fits the standard viewport width",
                ["Check for horizontal overflow at the standard browser viewport"],
                "The page does not overflow horizontally at the standard viewport.",
                test_type="Smoke",
            ),
            _create_basic_test_case(
                "SMK-018",
                "Verify the page has a non-empty meta description",
                ["Inspect the description meta element when one is configured"],
                "A configured description meta element contains text.",
            ),
            _create_basic_test_case(
                "SMK-019",
                "Verify the page does not trigger an automatic refresh",
                ["Inspect meta elements for timed page refresh directives"],
                "No timed meta refresh directive is present.",
                test_type="Smoke",
            ),
            _create_basic_test_case(
                "SMK-020",
                "Verify element identifiers are unique",
                ["Check the document for repeated id values"],
                "Every id value is unique within the document.",
                test_type="Accessibility",
            ),
        ]
    )
    return test_cases


def _create_basic_test_case(
    test_case_id: str,
    title: str,
    steps: list[str],
    expected_result: str,
    *,
    test_type: str = "Accessibility",
) -> SmokeTestCase:
    return SmokeTestCase(
        test_case_id=test_case_id,
        title=title,
        priority="Medium",
        type=test_type,
        preconditions=["The homepage has loaded successfully"],
        steps=[*steps, "Do not enter data or activate controls"],
        expected_result=expected_result,
        automation_candidate=True,
    )
