"""Shared fixtures: temp-dir settings, sample CSVs and a scripted fake LLM."""

import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.llm.prompts import CODEGEN_SYSTEM, EXPLAINER_SYSTEM, FOLLOW_UP_SYSTEM, PLANNER_SYSTEM

SALES_CSV = """order_id,Order Date,Region,Revenue
1,2024-01-05,North,"$1,200.50"
2,2024-02-10,South,800
3,2024-03-15,North,950
4,2024-04-20,East,
5,2024-05-25,South,1100
5,2024-05-25,South,1100
"""

TARGETS_CSV = """region,target
North,2000
South,1500
East,900
"""


class FakeLLM:
    """Returns scripted replies keyed on which prompt is being answered."""

    def __init__(
        self, code_replies: list[str], plan: str | None = None, follow_ups: list[dict] | None = None
    ) -> None:
        self.code_replies = list(code_replies)
        self.plan = plan or '{"output_type": "mixed", "datasets": [], "steps": ["sum"], "assumptions": []}'
        self.codegen_calls = 0
        self.follow_ups = follow_ups if follow_ups is not None else []

    def complete(self, system: str, user: str) -> str:
        if system == PLANNER_SYSTEM:
            return self.plan
        if system == CODEGEN_SYSTEM:
            self.codegen_calls += 1
            reply = self.code_replies[min(self.codegen_calls - 1, len(self.code_replies) - 1)]
            return f"```python\n{reply}\n```"
        if system == FOLLOW_UP_SYSTEM:
            return json.dumps({"suggestions": self.follow_ups})
        assert system == EXPLAINER_SYSTEM
        return "Total revenue is **as computed**."


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", sandbox_timeout_seconds=60, _env_file=None)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def csv_file(name: str, content: str) -> tuple[str, tuple[str, io.BytesIO, str]]:
    return ("files", (name, io.BytesIO(content.encode()), "text/csv"))
