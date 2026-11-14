"""Automatic inference of joinable columns between datasets."""

from dataclasses import dataclass

import pandas as pd

from app.schemas.dataset import ColumnMeta

_JOINABLE_KINDS = {"integer", "categorical", "text"}
_MAX_VALUES = 50_000
_VALUE_ONLY_MIN_UNIQUE = 5


@dataclass(frozen=True)
class DatasetRef:
    """The minimum a dataset needs to expose for relationship inference."""

    id: str
    parquet_path: str
    columns: list[ColumnMeta]


@dataclass(frozen=True)
class RelationshipCandidate:
    left_dataset_id: str
    left_column: str
    right_dataset_id: str
    right_column: str
    overlap: float


def _names_related(a: str, b: str) -> bool:
    """Equal names, or one name is a suffix of the other (`id` vs `customer_id`)."""
    return a == b or a.endswith(f"_{b}") or b.endswith(f"_{a}")


def _values(ref: DatasetRef, column: str) -> set[str]:
    series = pd.read_parquet(ref.parquet_path, columns=[column])[column].dropna()
    return set(series.astype(str).drop_duplicates().head(_MAX_VALUES))


def _overlap(left: set[str], right: set[str]) -> float:
    smaller = min(len(left), len(right))
    return len(left & right) / smaller if smaller else 0.0


def infer_relationships(
    new: DatasetRef, existing: list[DatasetRef], min_overlap: float = 0.5
) -> list[RelationshipCandidate]:
    """Find column pairs between `new` and each existing dataset that look joinable.

    A pair qualifies when value overlap is high AND either the names are related
    or both columns are string-like with enough distinct values (guards against
    small integer columns matching by coincidence).
    """
    found: list[RelationshipCandidate] = []
    for other in existing:
        for left in (c for c in new.columns if c.kind in _JOINABLE_KINDS):
            for right in (c for c in other.columns if c.kind == left.kind or {c.kind, left.kind} <= {"categorical", "text"}):
                name_match = _names_related(left.name, right.name)
                string_like = left.kind != "integer"
                value_only = (
                    string_like
                    and min(left.unique_count, right.unique_count) >= _VALUE_ONLY_MIN_UNIQUE
                )
                if not (name_match or value_only):
                    continue
                overlap = _overlap(_values(new, left.name), _values(other, right.name))
                threshold = min_overlap if name_match else max(min_overlap, 0.8)
                if overlap >= threshold:
                    found.append(
                        RelationshipCandidate(new.id, left.name, other.id, right.name, round(overlap, 3))
                    )
    return found
