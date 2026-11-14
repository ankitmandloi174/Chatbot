"""Natural-language explanation of computed results."""

import json

import pandas as pd

from app.services.analysis.models import AnalysisPlan, ExecutionResult
from app.services.llm.client import LLM
from app.services.llm.prompts import EXPLAINER_SYSTEM, explainer_user_prompt

_PREVIEW_ROWS = 30


def result_to_text(execution: ExecutionResult) -> str:
    """Compact text rendering of a result for the explainer prompt."""
    result = execution.result
    if result["kind"] == "table":
        frame = pd.DataFrame(result["rows"], columns=result["columns"])
        text = frame.head(_PREVIEW_ROWS).to_string(index=False)
        return f"{text}\n(total rows: {result['total_rows']})"
    return json.dumps(result["value"], default=str)


class ResultExplainer:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def explain(
        self, question: str, plan: AnalysisPlan, execution: ExecutionResult, schema_text: str
    ) -> str:
        prompt = explainer_user_prompt(question, plan.model_dump_json(), result_to_text(execution), schema_text)
        return self._llm.complete(EXPLAINER_SYSTEM, prompt).strip()
