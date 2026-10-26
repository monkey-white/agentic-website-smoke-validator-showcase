from pydantic import BaseModel


class SmokeTestCase(BaseModel):
    test_case_id: str
    title: str
    priority: str
    type: str
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    automation_candidate: bool