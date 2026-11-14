"""Headline metrics (KPIs) extracted from a computed result."""

from typing import Any

_MAX_KPIS = 6


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def extract_kpis(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return `{label, value}` pairs for results that are a single number or a single row.

    Multi-row tables are deliberately not summarised: any aggregate chosen here
    (sum, mean, ...) could be meaningless for the user's question.
    """
    if result["kind"] == "scalar":
        return [{"label": "Result", "value": result["value"]}] if _is_number(result["value"]) else []

    if result["kind"] == "table" and result["total_rows"] == 1 and result["rows"]:
        pairs = zip(result["columns"], result["rows"][0])
        return [{"label": c, "value": v} for c, v in pairs if _is_number(v)][:_MAX_KPIS]
    return []
