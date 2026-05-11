from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ChartHint(str, Enum):
    table = "table"
    bar = "bar"
    line = "line"
    pie = "pie"
    scalar = "scalar"


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    database_id: str = Field(min_length=1, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)


class LLMOutput(BaseModel):
    """The structured-output contract Gemini fills in.

    Kept separate from the API response so adding result fields
    (rows / columns / attempts) doesn't change the LLM schema.
    """

    sql: str
    explanation: str
    chart_hint: ChartHint


class QueryResponse(BaseModel):
    sql: str
    explanation: str
    chart_hint: ChartHint
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    attempts: int = 1
    session_id: str
