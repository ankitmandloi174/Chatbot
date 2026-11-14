"""Combines data-driven and LLM follow-ups behind one validation gate."""

import logging

from app.services.suggestions.candidates import generate_candidates
from app.services.suggestions.llm_suggester import LLMSuggester
from app.services.suggestions.models import FollowUpContext, Suggestion
from app.services.suggestions.validator import validate

logger = logging.getLogger(__name__)


class FollowUpService:
    """Never raises: follow-ups are an enhancement, so a failure just yields fewer of them."""

    def __init__(self, suggester: LLMSuggester | None, max_follow_ups: int) -> None:
        self._suggester = suggester
        self._max = max_follow_ups

    def suggest(self, context: FollowUpContext) -> list[str]:
        """Result-specific LLM questions first, topped up with profile-based ones, all validated."""
        try:
            candidates = generate_candidates(context)
        except Exception:  # defensive: bad profile data must not break the answer
            logger.exception("follow-up candidate generation failed")
            candidates = []
        valid = validate([*self._from_llm(context, candidates), *candidates], context)
        return [s.question for s in valid[: self._max]]

    def _from_llm(self, context: FollowUpContext, covered: list[Suggestion]) -> list[Suggestion]:
        if self._suggester is None:
            return []
        try:
            return self._suggester.suggest(context, covered)
        except Exception as exc:  # network, provider or malformed-JSON errors
            logger.warning("LLM follow-ups unavailable: %s", exc)
            return []
