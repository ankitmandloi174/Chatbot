"""ChromaDB-backed vector index over dataset columns."""

import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.models.dataset import Dataset

logger = logging.getLogger(__name__)
_COLLECTION = "dataset_columns"


class VectorStoreError(RuntimeError):
    """Raised when the vector index cannot be used."""


def column_document(table_name: str, column: dict) -> str:
    """Text that gets embedded for one column."""
    samples = ", ".join(column.get("samples", []))
    return (
        f"table {table_name} column {column['name'].replace('_', ' ')} "
        f"({column['kind']}) examples: {samples}"
    )


class ColumnVectorStore:
    """Indexes one document per column; ids are `<dataset_id>::<column>`."""

    def __init__(self, persist_dir: Path) -> None:
        self._client = chromadb.PersistentClient(
            path=str(persist_dir), settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._collection = self._client.get_or_create_collection(
            _COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    def add_dataset(self, dataset: Dataset) -> None:
        try:
            self._collection.upsert(
                ids=[f"{dataset.id}::{c['name']}" for c in dataset.columns],
                documents=[column_document(dataset.table_name, c) for c in dataset.columns],
                metadatas=[{"dataset_id": dataset.id, "column": c["name"]} for c in dataset.columns],
            )
        except Exception as exc:  # embedding model download / chroma errors
            raise VectorStoreError(f"indexing failed: {exc}") from exc

    def delete_dataset(self, dataset_id: str) -> None:
        try:
            self._collection.delete(where={"dataset_id": dataset_id})
        except Exception as exc:
            raise VectorStoreError(f"delete failed: {exc}") from exc

    def query(self, text: str, dataset_ids: list[str], limit: int) -> list[tuple[str, str]]:
        """Return ranked `(dataset_id, column)` pairs most similar to `text`."""
        try:
            result = self._collection.query(
                query_texts=[text],
                n_results=limit,
                where={"dataset_id": {"$in": dataset_ids}},
            )
        except Exception as exc:
            raise VectorStoreError(f"query failed: {exc}") from exc
        return [(m["dataset_id"], m["column"]) for m in (result["metadatas"] or [[]])[0]]
