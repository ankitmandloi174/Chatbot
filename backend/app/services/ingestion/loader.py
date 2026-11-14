"""CSV loading and upload-level validation."""

import csv
from pathlib import Path

import pandas as pd

from app.core.exceptions import BadRequestError

NA_TOKENS = ["", "na", "n/a", "NA", "N/A", "null", "NULL", "none", "None", "nan", "NaN", "-", "?"]
_ENCODINGS = ("utf-8-sig", "latin-1")
_DELIMITERS = ",;\t|"


def validate_filename(filename: str) -> None:
    if not filename.lower().endswith(".csv"):
        raise BadRequestError(f"'{filename}' is not a .csv file")


def _sniff_delimiter(path: Path, encoding: str) -> str:
    with path.open("r", encoding=encoding, errors="replace") as handle:
        sample = handle.read(65536)
    try:
        return csv.Sniffer().sniff(sample, delimiters=_DELIMITERS).delimiter
    except csv.Error:
        return ","


def load_csv(path: Path) -> pd.DataFrame:
    """Read a CSV, trying common encodings and sniffing the delimiter."""
    if path.stat().st_size == 0:
        raise BadRequestError("file is empty")

    last_error: Exception | None = None
    for encoding in _ENCODINGS:
        try:
            df = pd.read_csv(
                path,
                sep=_sniff_delimiter(path, encoding),
                encoding=encoding,
                na_values=NA_TOKENS,
                keep_default_na=True,
                low_memory=False,
            )
            break
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            last_error = exc
    else:
        raise BadRequestError(f"could not parse CSV: {last_error}")

    if df.shape[1] == 0 or df.shape[0] == 0:
        raise BadRequestError("CSV has no data rows or columns")
    return df
