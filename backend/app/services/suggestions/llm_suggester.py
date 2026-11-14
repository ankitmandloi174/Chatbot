"""LLM-written follow-ups that depend on the actual result (e.g. "why is North highest?")."""

from collections.abc import Sequence
from typing import Any

from app.services.llm.client import LLM, parse_json_object
from app.services.llm.prompts import FOLLOW_UP_SYSTEM, follow_up_user_prompt
from app.services.suggestions.models import ColumnRef, FollowUpContext, Suggestion

_SAMPLE_VALUES = 5
_NONE = "(none)"


def render_catalog(context: FollowUpContext) -> str:
    """Every column of the relevant datasets, so the model cannot pick unrelated ones."""
    lines: list[str] = []
    for profile in context.scope:
        lines.append(f"{profile.table_name} (file: {profile.file_name}, {profile.row_count} rows)")
        for column in profile.columns:
            examples = f"; e.g. {', '.join(column.samples[:_SAMPLE_VALUES])}" if column.samples else ""
            lines.append(f"  - {column.name} ({column.kind}{examples})")
    return "\n".join(lines)


def _bullets(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or _NONE


def _parse(reply: str, limit: int) -> list[Suggestion]:
    """Turn the model's JSON into suggestions; malformed entries are skipped."""
    items: list[Any] = parse_json_object(reply).get("suggestions", [])
    suggestions: list[Suggestion] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("question"), str):
            continue
        refs = tuple(
            ColumnRef(*label.split(".", 1))
            for label in item.get("columns") or []
            if isinstance(label, str) and "." in label
        )
        suggestions.append(Suggestion(item["question"].strip(), "insight", refs))
    return suggestions[:limit]


class LLMSuggester:
    """Asks the model for result-specific follow-ups; output still goes through the validator."""

    def __init__(self, llm: LLM, limit: int) -> None:
        self._llm = llm
        self._limit = limit

    def suggest(self, context: FollowUpContext, covered: Sequence[Suggestion]) -> list[Suggestion]:
        prompt = follow_up_user_prompt(
            context.question,
            context.result_text,
            ", ".join(ref.label for ref in context.used) or _NONE,
            render_catalog(context),
            _bullets(context.previous_questions),
            _bullets([s.question for s in covered]),
        )
        return _parse(self._llm.complete(FOLLOW_UP_SYSTEM, prompt), self._limit)
