"""Column-level metadata extraction."""

import pandas as pd
from pandas.api import types as ptypes

from app.schemas.dataset import ColumnMeta

_CATEGORICAL_MAX_UNIQUE = 50
_SAMPLE_COUNT = 5
_SAMPLE_MAX_CHARS = 40


def column_kind(series: pd.Series) -> str:
    """Coarse semantic type used for prompts, retrieval and join inference."""
    if ptypes.is_bool_dtype(series):
        return "boolean"
    if ptypes.is_datetime64_any_dtype(series):
        return "datetime"
    if ptypes.is_integer_dtype(series):
        return "integer"
    if ptypes.is_numeric_dtype(series):
        return "numeric"
    unique = series.nunique(dropna=True)
    if unique <= _CATEGORICAL_MAX_UNIQUE or unique <= 0.5 * max(len(series), 1):
        return "categorical"
    return "text"


def _samples(series: pd.Series, kind: str) -> list[str]:
    non_null = series.dropna()
    values = (
        non_null.value_counts().head(_SAMPLE_COUNT).index
        if kind == "categorical"
        else non_null.drop_duplicates().head(_SAMPLE_COUNT)
    )
    return [str(v)[:_SAMPLE_MAX_CHARS] for v in values]


def _range(series: pd.Series, kind: str) -> tuple[float | str | None, float | str | None]:
    if series.dropna().empty or kind in {"boolean", "categorical", "text"}:
        return None, None
    low, high = series.min(), series.max()
    if kind == "datetime":
        return str(low.date()), str(high.date())
    return float(low), float(high)


def build_column_metadata(df: pd.DataFrame) -> list[ColumnMeta]:
    """Describe every column: dtype, kind, nulls, cardinality, range, samples."""
    metadata: list[ColumnMeta] = []
    for name in df.columns:
        series = df[name]
        kind = column_kind(series)
        low, high = _range(series, kind)
        mean = float(series.mean()) if kind in {"integer", "numeric"} and series.notna().any() else None
        metadata.append(
            ColumnMeta(
                name=name,
                dtype=str(series.dtype),
                kind=kind,
                null_count=int(series.isna().sum()),
                unique_count=int(series.nunique(dropna=True)),
                min=low,
                max=high,
                mean=mean,
                samples=_samples(series, kind),
            )
        )
    return metadata
