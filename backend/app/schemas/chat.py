"""Pydantic schemas for conversations and chat."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    dataset_ids: list[str] | None = Field(
        default=None, description="Restrict analysis to these datasets (default: all)."
    )


class TablePayload(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    truncated: bool = False


class KpiOut(BaseModel):
    label: str
    value: float | int


class SourceOut(BaseModel):
    """A dataset the generated code used, and which of its columns it referenced."""

    table_name: str
    file_name: str
    columns: list[str] = Field(default_factory=list)


class RetrievedDatasetTrace(BaseModel):
    table_name: str
    file_name: str
    columns: list[str]
    total_columns: int


class RelationshipTrace(BaseModel):
    left: str  # "table.column"
    right: str
    overlap: float


class AttemptTrace(BaseModel):
    attempt: int
    code: str
    validation: str  # passed | failed | skipped
    execution: str
    error: str | None = None
    duration_ms: int = 0


class ExecutionTrace(BaseModel):
    """Everything needed to show how an answer was produced."""

    retrieval_method: str
    carried_over: list[str] = Field(default_factory=list)  # "table.column" reused from the previous answer
    retrieved: list[RetrievedDatasetTrace] = Field(default_factory=list)
    relationships: list[RelationshipTrace] = Field(default_factory=list)
    attempts: list[AttemptTrace] = Field(default_factory=list)
    retrieval_ms: int = 0
    planning_ms: int = 0
    explain_ms: int = 0


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    tables: list[TablePayload] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)  # Plotly figure JSON
    code: str | None = None
    plan: dict[str, Any] | None = None
    attempts: int = 0
    error: str | None = None
    kpis: list[KpiOut] = Field(default_factory=list)
    sources: list[SourceOut] = Field(default_factory=list)
    trace: ExecutionTrace | None = None
    followups: list[str] = Field(default_factory=list)


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
