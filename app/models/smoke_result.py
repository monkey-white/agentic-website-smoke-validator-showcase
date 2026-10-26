from pydantic import BaseModel


class SmokeTestResult(BaseModel):
    test_case_id: str
    title: str
    status: str
    actual_result: str
    duration_seconds: float
    console_errors: list[str]
    network_errors: list[str]
    notes: list[str]
