"""DataFrame cleaning: names, types, duplicates, missing values, outliers.

Missing values are handled conservatively (no heavy imputation) and outliers
are only *flagged*, never removed, so analysis stays faithful to the source.
"""

import re
import warnings

import pandas as pd
from pandas.api import types as ptypes

from app.schemas.dataset import CleaningReport

_NUMERIC_NOISE = re.compile(r"[,$€£₹%\s]")
_BOOL_MAP = {"true": True, "false": False, "yes": True, "no": False}
_PARSE_THRESHOLD = 0.9
_DATE_SAMPLE = 200


def normalize_column_names(columns: list[object]) -> list[str]:
    """snake_case, strip symbols, and de-duplicate column names."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for index, raw in enumerate(columns):
        name = re.sub(r"[^0-9a-zA-Z]+", "_", str(raw).strip()).strip("_").lower() or f"column_{index}"
        if name[0].isdigit():
            name = f"c_{name}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        result.append(name if count == 0 else f"{name}_{count + 1}")
    return result


def _parse_ratio(parsed: pd.Series, original: pd.Series) -> float:
    non_null = original.notna().sum()
    return float(parsed.notna().sum() / non_null) if non_null else 0.0


def _try_boolean(series: pd.Series) -> pd.Series | None:
    lowered = series.str.lower()
    if lowered.dropna().isin(_BOOL_MAP).all() and lowered.notna().any():
        return lowered.map(_BOOL_MAP).astype("boolean")
    return None


def _try_numeric(series: pd.Series) -> pd.Series | None:
    parsed = pd.to_numeric(series.str.replace(_NUMERIC_NOISE, "", regex=True), errors="coerce")
    if _parse_ratio(parsed, series) < _PARSE_THRESHOLD:
        return None
    # Use plain numpy dtypes (not nullable Int64/Float64) so later steps behave predictably.
    parsed = parsed.astype("float64")
    if parsed.notna().all() and (parsed % 1 == 0).all():
        return parsed.astype("int64")
    return parsed


def _to_datetime(values: pd.Series) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(values, errors="coerce", format="mixed")


def _try_datetime(series: pd.Series) -> pd.Series | None:
    sample = series.dropna().head(_DATE_SAMPLE)
    if sample.empty or _parse_ratio(_to_datetime(sample), sample) < _PARSE_THRESHOLD:
        return None
    parsed = _to_datetime(series)
    return parsed if _parse_ratio(parsed, series) >= _PARSE_THRESHOLD else None


def _coerce_types(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    for column in df.columns[df.dtypes == "object"]:
        series = df[column].astype("string").str.strip().replace("", pd.NA)
        for label, converter in (
            ("boolean", _try_boolean),
            ("numeric", _try_numeric),
            ("datetime", _try_datetime),
        ):
            converted = converter(series)
            if converted is not None:
                df[column] = converted
                report.type_conversions[column] = label
                break
        else:
            df[column] = series.astype(object).where(series.notna(), None)
    return df


def _handle_missing(
    df: pd.DataFrame, report: CleaningReport, max_null_ratio: float, median_fill_ratio: float
) -> pd.DataFrame:
    total = len(df)
    drop = [c for c in df.columns if df[c].isna().mean() > max_null_ratio]
    if drop:
        df = df.drop(columns=drop)
        report.dropped_columns.extend(drop)

    for column in df.columns:
        nulls = int(df[column].isna().sum())
        if not nulls:
            continue
        ratio = nulls / total
        series = df[column]
        if ptypes.is_bool_dtype(series) or ptypes.is_datetime64_any_dtype(series):
            report.missing_left[column] = nulls
        elif ptypes.is_numeric_dtype(series):
            if ratio <= median_fill_ratio:
                df[column] = series.fillna(series.median())
                report.missing_filled[column] = f"median ({nulls} values)"
            else:
                report.missing_left[column] = nulls
        else:
            df[column] = series.fillna("Unknown")
            report.missing_filled[column] = f"'Unknown' ({nulls} values)"
    return df


def _flag_outliers(df: pd.DataFrame, report: CleaningReport) -> None:
    for column in df.select_dtypes(include="number").columns:
        series = df[column].dropna()
        if series.nunique() < 5:
            continue
        q1, q3 = series.quantile([0.25, 0.75])
        spread = 1.5 * (q3 - q1)
        count = int(((series < q1 - spread) | (series > q3 + spread)).sum())
        if count:
            report.outliers_flagged[column] = count


def clean_dataframe(
    df: pd.DataFrame, max_null_ratio: float = 0.9, median_fill_ratio: float = 0.05
) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean a raw DataFrame and describe every change made."""
    report = CleaningReport(rows_before=len(df))
    df = df.copy()

    new_names = normalize_column_names(list(df.columns))
    report.renamed_columns = {str(o): n for o, n in zip(df.columns, new_names) if str(o) != n}
    df.columns = new_names

    before = len(df)
    df = df.dropna(how="all").dropna(axis=1, how="all")
    report.empty_rows_removed = before - len(df)

    df = _coerce_types(df, report)

    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    report.duplicates_removed = before - len(df)

    df = _handle_missing(df, report, max_null_ratio, median_fill_ratio)
    _flag_outliers(df, report)

    report.rows_after = len(df)
    return df, report
