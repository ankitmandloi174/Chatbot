"""Deterministic follow-ups built from the dataset profile.

Every candidate is constructed from real column names and values, so it is grounded by
construction. Each "move" is a different analytical direction relative to what the
answer just did, and each move yields at most one candidate for variety.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from app.schemas.dataset import ColumnMeta
from app.services.suggestions.language import humanize
from app.services.suggestions.models import ColumnRef, FollowUpContext, Suggestion, TableProfile

_MAX_GROUPS = 12  # a category with more values is not a useful breakdown
_ID_LIKE = re.compile(r"(^|_)id$")
_MIN_TREND_DAYS = 60
_MIN_WINDOW_DAYS = 180
_RANKING_MIN_ROWS = 10


def _is_measure(column: ColumnMeta, rows: int) -> bool:
    if _ID_LIKE.search(column.name):
        return False
    # A fully unique integer column is an identifier, not something to aggregate.
    return column.kind == "numeric" or (column.kind == "integer" and column.unique_count < rows)


def _is_dimension(column: ColumnMeta) -> bool:
    return column.kind == "categorical" and 2 <= column.unique_count <= _MAX_GROUPS


def _span_days(column: ColumnMeta) -> int | None:
    try:
        return (pd.to_datetime(column.max) - pd.to_datetime(column.min)).days
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class _View:
    """One dataset the answer touched, with the columns it used."""

    profile: TableProfile
    used: tuple[ColumnMeta, ...]

    @property
    def measure(self) -> ColumnMeta | None:
        rows = self.profile.row_count
        used = next((c for c in self.used if _is_measure(c, rows)), None)
        return used or next((c for c in self.profile.columns if _is_measure(c, rows)), None)

    @property
    def used_dimensions(self) -> list[ColumnMeta]:
        return [c for c in self.used if _is_dimension(c)]

    @property
    def free_dimensions(self) -> list[ColumnMeta]:
        used = {c.name for c in self.used}
        return [c for c in self.profile.columns if _is_dimension(c) and c.name not in used]

    @property
    def date(self) -> ColumnMeta | None:
        dates = [c for c in self.profile.columns if c.kind == "datetime"]
        return next((c for c in dates if c in self.used), dates[0] if dates else None)

    @property
    def time_used(self) -> bool:
        return any(c.kind == "datetime" for c in self.used)

    def ref(self, column: ColumnMeta) -> ColumnRef:
        return ColumnRef(self.profile.table_name, column.name)


def _views(context: FollowUpContext) -> list[_View]:
    used_names: dict[str, set[str]] = {}
    for ref in context.used:
        used_names.setdefault(ref.table, set()).add(ref.column)
    focus = [p for p in context.profiles if p.table_name in used_names] or list(context.profiles)
    return [
        _View(p, tuple(c for c in p.columns if c.name in used_names.get(p.table_name, set())))
        for p in focus
    ]


Move = Callable[[FollowUpContext, _View], Suggestion | None]


def _where(context: FollowUpContext, view: _View) -> str:
    """Name the file when several datasets are selected so retrieval picks the right one."""
    return f" in {view.profile.label}" if len(context.profiles) > 1 else ""


def _break_down(context: FollowUpContext, view: _View) -> Suggestion | None:
    if not view.free_dimensions:
        return None
    dimension, measure, where = view.free_dimensions[0], view.measure, _where(context, view)
    if measure is None:
        text = f"Count records by {humanize(dimension.name)}{where}"
        return Suggestion(text, "break_down", (view.ref(dimension),))
    text = f"Break down {humanize(measure.name)} by {humanize(dimension.name)}{where}"
    return Suggestion(text, "break_down", (view.ref(measure), view.ref(dimension)))


def _trend(context: FollowUpContext, view: _View) -> Suggestion | None:
    date, measure = view.date, view.measure
    if view.time_used or date is None or measure is None or (_span_days(date) or 0) < _MIN_TREND_DAYS:
        return None
    text = f"Show the monthly trend of {humanize(measure.name)}{_where(context, view)}"
    return Suggestion(text, "trend", (view.ref(measure), view.ref(date)))


def _change_window(context: FollowUpContext, view: _View) -> Suggestion | None:
    date, measure = view.date, view.measure
    if not view.time_used or date is None or measure is None or (_span_days(date) or 0) < _MIN_WINDOW_DAYS:
        return None
    text = (
        f"Compare {humanize(measure.name)} in the last 3 months with the 3 months before"
        f"{_where(context, view)}"
    )
    return Suggestion(text, "change_window", (view.ref(measure), view.ref(date)))


def _ranking(context: FollowUpContext, view: _View) -> Suggestion | None:
    if (context.result_rows or 0) <= _RANKING_MIN_ROWS or not view.used_dimensions or view.measure is None:
        return None
    dimension, measure = view.used_dimensions[0], view.measure
    text = f"Show the top 10 {humanize(dimension.name)} by {humanize(measure.name)}{_where(context, view)}"
    return Suggestion(text, "ranking", (view.ref(dimension), view.ref(measure)))


def _cross_file(context: FollowUpContext, view: _View) -> Suggestion | None:
    for join in context.joins:
        mine, other = (join.left, join.right) if join.left.table == view.profile.table_name else (join.right, join.left)
        if mine.table != view.profile.table_name or other.table in context.used_tables:
            continue
        partner = next((p for p in context.profiles if p.table_name == other.table), None)
        measure = next((c for c in partner.columns if _is_measure(c, partner.row_count)), None) if partner else None
        if partner is None or measure is None:
            continue
        text = (
            f"Combine {view.profile.label} and {partner.label} on {humanize(mine.column)} "
            f"and compare {humanize(measure.name)}"
        )
        return Suggestion(text, "cross_file", (mine, ColumnRef(partner.table_name, measure.name)))
    return None


def _focus(context: FollowUpContext, view: _View) -> Suggestion | None:
    measure = view.measure
    dimension = next((d for d in view.used_dimensions if d.samples), None)
    if measure is None or dimension is None:
        return None
    text = (
        f"Compare {humanize(measure.name)} for {dimension.samples[0]} with the average across all "
        f"{humanize(dimension.name)} values{_where(context, view)}"
    )
    return Suggestion(text, "focus", (view.ref(measure), view.ref(dimension)))


def _outliers(context: FollowUpContext, view: _View) -> Suggestion | None:
    column = next(
        (c for c in view.used if _is_measure(c, view.profile.row_count) and view.profile.outliers.get(c.name)),
        None,
    )
    if column is None:
        return None
    text = f"Which rows have unusually high or low {humanize(column.name)}{_where(context, view)}?"
    return Suggestion(text, "outliers", (view.ref(column),))


def _data_quality(context: FollowUpContext, view: _View) -> Suggestion | None:
    column = next((c for c in view.used if view.profile.missing.get(c.name)), None)
    if column is None:
        return None
    text = f"How many rows are missing {humanize(column.name)}{_where(context, view)}?"
    return Suggestion(text, "data_quality", (view.ref(column),))


# Order is priority: the most useful analytical directions come first.
_MOVES: tuple[Move, ...] = (
    _break_down, _trend, _change_window, _ranking, _cross_file, _focus, _outliers, _data_quality,
)


def generate_candidates(context: FollowUpContext) -> list[Suggestion]:
    """At most one candidate per move, in priority order."""
    views = _views(context)
    found: list[Suggestion] = []
    for move in _MOVES:
        suggestion = next((s for view in views if (s := move(context, view))), None)
        if suggestion:
            found.append(suggestion)
    return found
