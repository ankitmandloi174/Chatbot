import io

import pandas as pd

from app.services.ingestion.cleaning import clean_dataframe, normalize_column_names
from app.services.ingestion.metadata import build_column_metadata
from tests.conftest import SALES_CSV


def _clean(csv: str = SALES_CSV):
    return clean_dataframe(pd.read_csv(io.StringIO(csv)))


def test_normalizes_and_dedupes_names():
    assert normalize_column_names(["Order Date", "order_date", "1st Col", " "]) == [
        "order_date", "order_date_2", "c_1st_col", "column_3",
    ]


def test_types_duplicates_and_missing_values():
    df, report = _clean()
    assert str(df["order_date"].dtype).startswith("datetime64")
    assert df["revenue"].dtype.kind == "f"
    assert df["revenue"].iloc[0] == 1200.5  # "$1,200.50" parsed
    assert report.duplicates_removed == 1
    assert "revenue" in report.missing_left  # 1/5 nulls: too many to median-fill, left as NaN


def test_small_null_ratio_is_median_filled():
    values = [str(i) for i in range(1, 41)] + [""]
    df, report = clean_dataframe(pd.DataFrame({"amount": values}))
    assert df["amount"].isna().sum() == 0
    assert "amount" in report.missing_filled


def test_categorical_nulls_become_unknown_and_sparse_columns_dropped():
    raw = pd.DataFrame({"city": ["a", None] + [f"b{i}" for i in range(18)], "junk": [None, 1] + [None] * 18})
    df, report = clean_dataframe(raw)
    assert "Unknown" in df["city"].tolist()
    assert report.dropped_columns == ["junk"]


def test_outliers_are_flagged_not_removed():
    raw = pd.DataFrame({"v": [10, 11, 12, 13, 14, 15, 16, 17, 9999]})
    df, report = clean_dataframe(raw)
    assert report.outliers_flagged == {"v": 1}
    assert len(df) == len(raw)


def test_metadata_kinds_and_nulls():
    df, _ = _clean()
    meta = {c.name: c for c in build_column_metadata(df)}
    assert meta["order_date"].kind == "datetime"
    assert meta["order_date"].min == "2024-01-05"
    assert meta["revenue"].null_count == 1
    assert meta["region"].kind == "categorical"
