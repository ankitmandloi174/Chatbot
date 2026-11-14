"""Orchestrates dataset ingestion: load -> clean -> profile -> persist -> index."""

import keyword
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models.dataset import Dataset, DatasetRelationship
from app.repositories.dataset_repository import DatasetRepository
from app.schemas.dataset import CleaningReport, ColumnMeta
from app.services.ingestion.cleaning import clean_dataframe
from app.services.ingestion.loader import load_csv
from app.services.ingestion.metadata import build_column_metadata
from app.services.ingestion.relationships import DatasetRef, infer_relationships
from app.services.retrieval.vector_store import ColumnVectorStore, VectorStoreError

logger = logging.getLogger(__name__)

# Names the sandbox injects; a dataset variable must never shadow them.
RESERVED_NAMES = {"pd", "np", "px", "go", "dfs", "result", "fig"}


@dataclass
class PreparedDataset:
    """Output of the CPU-heavy, thread-safe stage of ingestion."""

    dataset_id: str
    name: str
    table_name: str
    parquet_path: Path
    row_count: int
    columns: list[ColumnMeta]
    report: CleaningReport


def slugify_table_name(filename: str, taken: set[str]) -> str:
    """Build a unique, valid Python identifier from a file name."""
    base = re.sub(r"[^0-9a-zA-Z]+", "_", Path(filename).stem).strip("_").lower() or "dataset"
    if base[0].isdigit():
        base = f"t_{base}"
    if keyword.iskeyword(base) or base in RESERVED_NAMES:
        base = f"{base}_data"
    candidate, suffix = base, 2
    while candidate in taken:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def prepare_dataset(
    raw_path: Path, original_name: str, table_name: str, parquet_dir: Path, settings: Settings
) -> PreparedDataset:
    """Load, clean and profile one CSV, then write it as Parquet. Thread-safe."""
    raw = load_csv(raw_path)
    cleaned, report = clean_dataframe(
        raw, settings.max_null_ratio_to_keep_column, settings.median_fill_max_null_ratio
    )
    dataset_id = str(uuid4())
    parquet_path = parquet_dir / f"{dataset_id}.parquet"
    cleaned.to_parquet(parquet_path, index=False)
    return PreparedDataset(
        dataset_id=dataset_id,
        name=original_name,
        table_name=table_name,
        parquet_path=parquet_path,
        row_count=len(cleaned),
        columns=build_column_metadata(cleaned),
        report=report,
    )


class DatasetService:
    """Persistence-side operations for datasets (single-threaded, uses the DB session)."""

    def __init__(
        self, settings: Settings, repository: DatasetRepository, vector_store: ColumnVectorStore
    ) -> None:
        self._settings = settings
        self._repo = repository
        self._vectors = vector_store

    def reserve_table_names(self, filenames: list[str]) -> list[str]:
        """Allocate unique table names for a batch before parallel processing."""
        taken = self._repo.table_names()
        names: list[str] = []
        for filename in filenames:
            name = slugify_table_name(filename, taken)
            taken.add(name)
            names.append(name)
        return names

    def register(self, prepared: PreparedDataset) -> tuple[Dataset, list[DatasetRelationship]]:
        """Persist a prepared dataset, index its columns and infer relationships."""
        existing = [
            DatasetRef(d.id, d.parquet_path, [ColumnMeta(**c) for c in d.columns])
            for d in self._repo.list()
        ]
        dataset = self._repo.add(
            Dataset(
                id=prepared.dataset_id,
                name=prepared.name,
                table_name=prepared.table_name,
                parquet_path=str(prepared.parquet_path),
                row_count=prepared.row_count,
                column_count=len(prepared.columns),
                columns=[c.model_dump() for c in prepared.columns],
                cleaning_report=prepared.report.model_dump(),
            )
        )
        try:
            self._vectors.add_dataset(dataset)
        except VectorStoreError:
            logger.warning("vector indexing failed; keyword retrieval only", extra={"dataset": dataset.id})

        candidates = infer_relationships(
            DatasetRef(dataset.id, dataset.parquet_path, prepared.columns),
            existing,
            self._settings.relationship_min_overlap,
        )
        relationships = [DatasetRelationship(**vars(c)) for c in candidates]
        self._repo.add_relationships(relationships)
        logger.info(
            "dataset registered",
            extra={"dataset": dataset.id, "rows": dataset.row_count, "relationships": len(relationships)},
        )
        return dataset, relationships

    def list_datasets(self) -> list[Dataset]:
        return list(self._repo.list())

    def list_relationships(self) -> list[DatasetRelationship]:
        return list(self._repo.list_relationships())

    def delete(self, dataset_id: str) -> None:
        dataset = self._repo.get(dataset_id)
        if dataset is None:
            raise NotFoundError(f"Dataset {dataset_id} not found")
        try:
            self._vectors.delete_dataset(dataset_id)
        except VectorStoreError:
            logger.warning("vector delete failed", extra={"dataset": dataset_id})
        Path(dataset.parquet_path).unlink(missing_ok=True)
        self._repo.delete(dataset)
