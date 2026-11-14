"""Gate that drops follow-ups that are vague, repeated or not about the user's data."""

import logging
import re
from collections.abc import Iterable

from app.services.suggestions.language import mentions, similar
from app.services.suggestions.models import FollowUpContext, Suggestion

logger = logging.getLogger(__name__)

_MIN_WORDS = 4
_GENERIC = re.compile(
    r"^\W*(tell me more|what else|anything else|any other|can you (help|tell)|"
    r"what (other )?(insights?|questions?)|more (details?|information|insights?))",
    re.IGNORECASE,
)


def _rejection(suggestion: Suggestion, context: FollowUpContext, accepted: list[str]) -> str | None:
    """Why the suggestion must be dropped, or None when it is acceptable."""
    question = suggestion.question.strip()
    if len(question.split()) < _MIN_WORDS or _GENERIC.search(question):
        return "generic"
    if not suggestion.columns:
        return "no columns listed"

    known = {(p.table_name, c.name) for p in context.scope for c in p.columns}
    unknown = [ref.label for ref in suggestion.columns if tuple(ref) not in known]
    if unknown:
        return f"columns outside the relevant datasets: {', '.join(unknown)}"
    if not any(mentions(question, ref.column) for ref in suggestion.columns):
        return "does not mention any listed column"

    seen = [context.question, *context.previous_questions, *accepted]
    if any(similar(question, other) for other in seen):
        return "repeats an earlier question"
    return None


def validate(suggestions: Iterable[Suggestion], context: FollowUpContext) -> list[Suggestion]:
    """Keep, in order, only suggestions that are specific, grounded in the data and new."""
    kept: list[Suggestion] = []
    for suggestion in suggestions:
        reason = _rejection(suggestion, context, [s.question for s in kept])
        if reason:
            logger.info("follow-up rejected", extra={"question": suggestion.question, "reason": reason})
            continue
        kept.append(suggestion)
    return kept
