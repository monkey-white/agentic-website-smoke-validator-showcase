from pydantic import BaseModel

from app.models.test_case import SmokeTestCase


class TestPlanResponse(BaseModel):
    website_url: str
    test_count: int
    tests: list[SmokeTestCase]
