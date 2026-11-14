"""Plain value objects describing the data a follow-up may refer to.

They hold no ORM objects so a context can safely be used from a worker thread.
"""

from dataclasses import dataclass
from typing import NamedTuple

from app.schemas.dataset import ColumnMeta


class ColumnRef(NamedTuple):
    table: str
    column: str

    @property
    def label(self) -> str:
        return f"{self.table}.{self.column}"


@dataclass(frozen=True)
class TableProfile:
    """Full profile of one selected dataset (not just the retrieved columns)."""

    table_name: str
    file_name: str
    row_count: int
    columns: tuple[ColumnMeta, ...]
    missing: dict[str, int]  # column -> nulls left after cleaning
    outliers: dict[str, int]  # column -> values flagged as outliers

    def column(self, name: str) -> ColumnMeta | None:
        return next((c for c in self.columns if c.name == name), None)

    @property
    def label(self) -> str:
        return self.table_name.replace("_", " ")


@dataclass(frozen=True)
class JoinKey:
    left: ColumnRef
    right: ColumnRef


@dataclass(frozen=True)
class FollowUpContext:
    """Everything known about the turn that was just answered."""

    question: str
    profiles: tuple[TableProfile, ...]
    used: tuple[ColumnRef, ...]  # columns the generated code referenced
    joins: tuple[JoinKey, ...]
    result_text: str
    result_rows: int | None  # row count when the result was a table
    previous_questions: tuple[str, ...]

    @property
    def used_tables(self) -> set[str]:
        return {ref.table for ref in self.used}

    @property
    def scope(self) -> tuple[TableProfile, ...]:
        """Datasets a follow-up may touch: those the answer used plus ones joinable to them."""
        focus = self.used_tables or {p.table_name for p in self.profiles}
        reachable = set(focus)
        for join in self.joins:
            if join.left.table in focus:
                reachable.add(join.right.table)
            if join.right.table in focus:
                reachable.add(join.left.table)
        return tuple(p for p in self.profiles if p.table_name in reachable)


@dataclass(frozen=True)
class Suggestion:
    """A candidate question plus the columns it is about (so it can be verified)."""

    question: str
    move: str  # e.g. "break_down", "trend"; "insight" for LLM-written ones
    columns: tuple[ColumnRef, ...]
