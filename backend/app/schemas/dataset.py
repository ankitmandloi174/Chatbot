"""Pydantic schemas for datasets."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ColumnMeta(BaseModel):
    name: str
    dtype: str
    kind: str  # numeric | integer | datetime | boolean | categorical | text
    null_count: int
    unique_count: int
    min: float | str | None = None
    max: float | str | None = None
    mean: float | None = None
    samples: list[str] = Field(default_factory=list)


class CleaningReport(BaseModel):
    rows_before: int = 0
    rows_after: int = 0
    duplicates_removed: int = 0
    empty_rows_removed: int = 0
    dropped_columns: list[str] = Field(default_factory=list)
    renamed_columns: dict[str, str] = Field(default_factory=dict)
    type_conversions: dict[str, str] = Field(default_factory=dict)
    missing_filled: dict[str, str] = Field(default_factory=dict)
    missing_left: dict[str, int] = Field(default_factory=dict)
    outliers_flagged: dict[str, int] = Field(default_factory=dict)


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    table_name: str
    row_count: int
    column_count: int
    columns: list[ColumnMeta]
    cleaning_report: CleaningReport
    created_at: datetime


class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    left_dataset_id: str
    left_column: str
    right_dataset_id: str
    right_column: str
    overlap: float


class UploadFailure(BaseModel):
    filename: str
    error: str


class UploadResponse(BaseModel):
    datasets: list[DatasetOut]
    failures: list[UploadFailure]
    relationships: list[RelationshipOut]
