from enum import StrEnum

from pydantic import BaseModel, Field


class DiagnosticKind(StrEnum):
    CONSOLE = "console"
    FAILURE = "failure"
    NETWORK = "network"
    NOTE = "note"


class DiagnosticCandidate(BaseModel):
    diagnostic_id: str
    kind: DiagnosticKind
    message: str = Field(max_length=500)
    source_messages: list[str] = Field(min_length=1, max_length=5)


class DiagnosticAnalysis(BaseModel):
    kind: DiagnosticKind
    message: str
    related_message_count: int = Field(default=1, ge=1)
    related_messages: list[str] = Field(default_factory=list, max_length=5)
    explanation: str = Field(max_length=280)
    likely_impact: str = Field(max_length=180)
    recommended_follow_up: str = Field(max_length=180)
