from enum import Enum

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


class QueryResponse(BaseModel):
    sql: str
    explanation: str
    chart_hint: ChartHint
