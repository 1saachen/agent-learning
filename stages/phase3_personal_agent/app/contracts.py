from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _TrimmedTextModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def trim_text_fields(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class SearchNotesArgs(_TrimmedTextModel):
    query: str = Field(min_length=1, max_length=200)
    max_results: int = Field(default=5, ge=1, le=10)


class CreateTodoArgs(_TrimmedTextModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date | None = None
    priority: Literal["low", "medium", "high"] = "medium"


class GetWeatherArgs(_TrimmedTextModel):
    city: str = Field(min_length=1, max_length=100)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: str


class AssistantDecision(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ToolExecutionResult(BaseModel):
    ok: bool
    tool_name: str
    data: dict[str, Any] | list[Any] | None = None
    error_type: str | None = None
    message: str


class TraceEntry(BaseModel):
    step: int
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    ok: bool
    summary: str
    duration_ms: float = Field(ge=0)


class AgentRunResult(BaseModel):
    answer: str
    stop_reason: Literal["completed", "max_steps_exceeded", "model_error"]
    steps: int = Field(ge=0)
    trace: list[TraceEntry] = Field(default_factory=list)
