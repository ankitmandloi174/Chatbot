"""LLM-driven analysis planning."""

import logging

from pydantic import ValidationError

from app.services.analysis.models import AnalysisPlan
from app.services.llm.client import LLM, parse_json_object
from app.services.llm.prompts import PLANNER_SYSTEM, planner_user_prompt

logger = logging.getLogger(__name__)


class AnalysisPlanner:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def plan(self, question: str, schema_text: str, history_text: str) -> AnalysisPlan:
        """Ask the LLM for a plan; degrade to an empty plan if its JSON is unusable."""
        reply = self._llm.complete(PLANNER_SYSTEM, planner_user_prompt(question, schema_text, history_text))
        try:
            return AnalysisPlan.model_validate(parse_json_object(reply))
        except (ValueError, ValidationError):
            logger.warning("planner returned unparsable output; continuing with empty plan")
            return AnalysisPlan()
