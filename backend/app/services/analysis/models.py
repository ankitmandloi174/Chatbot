"""Value objects shared across the analysis package."""

from typing import Any, Literal

from pydantic import BaseModel, Field

OutputType = Literal["text", "table", "chart", "mixed"]
StepStatus = Literal["passed", "failed", "skipped"]


class ChartHint(BaseModel):
    type: str = "bar"
    x: str | None = None
    y: str | None = None
    title: str | None = None


class AnalysisPlan(BaseModel):
    output_type: OutputType = "text"
    datasets: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    chart: ChartHint | None = None
    assumptions: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    """What a successful sandbox run produced."""

    result: dict[str, Any]  # {"kind": "table"|"scalar"|"json", ...}
    figure: dict[str, Any] | None = None
    stdout: str = ""


class AttemptLog(BaseModel):
    """One generate -> validate -> execute cycle."""

    attempt: int
    code: str
    validation: StepStatus
    execution: StepStatus
    error: str | None = None
    duration_ms: int = 0


class AnalysisOutcome(BaseModel):
    """Final state of the plan -> code -> execute -> retry loop."""

    plan: AnalysisPlan
    code: str
    attempts: int
    execution: ExecutionResult | None = None
    error: str | None = None
    attempt_log: list[AttemptLog] = Field(default_factory=list)
    planning_ms: int = 0
    loaded_datasets: list[str] = Field(default_factory=list)  # table names given to the sandbox
