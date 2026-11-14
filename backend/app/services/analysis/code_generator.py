"""LLM-driven pandas code generation and repair."""

from app.services.analysis.models import AnalysisPlan
from app.services.llm.client import LLM, extract_fenced
from app.services.llm.prompts import CODEGEN_SYSTEM, REPAIR_ADDENDUM, codegen_user_prompt


class CodeGenerator:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def generate(
        self,
        question: str,
        plan: AnalysisPlan,
        schema_text: str,
        history_text: str,
        failed_code: str | None = None,
        error: str | None = None,
    ) -> str:
        """Generate code, or repair `failed_code` given its `error`."""
        prompt = codegen_user_prompt(question, plan.model_dump_json(indent=2), schema_text, history_text)
        if failed_code and error:
            prompt += "\n\n" + REPAIR_ADDENDUM.format(code=failed_code, error=error)
        return extract_fenced(self._llm.complete(CODEGEN_SYSTEM, prompt))
