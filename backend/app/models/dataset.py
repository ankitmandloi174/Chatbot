"""ORM models for datasets and inferred cross-dataset relationships."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255), unique=True)
    parquet_path: Mapped[str] = mapped_column(String(1024))
    row_count: Mapped[int] = mapped_column(Integer)
    column_count: Mapped[int] = mapped_column(Integer)
    columns: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    cleaning_report: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DatasetRelationship(Base):
    __tablename__ = "dataset_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    left_dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    left_column: Mapped[str] = mapped_column(String(255))
    right_dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    right_column: Mapped[str] = mapped_column(String(255))
    overlap: Mapped[float] = mapped_column(Float)
