from pydantic import BaseModel

from app.models.smoke_result import SmokeTestResult


class ExecutionEnvironment(BaseModel):
    browser_engine: str
    browser_version: str
    operating_system: str
    viewport_width: int
    viewport_height: int
    playwright_version: str


class SmokeTestExecution(BaseModel):
    results: list[SmokeTestResult]
    environment: ExecutionEnvironment
