"""Hybrid (keyword + vector) retrieval of relevant datasets and columns."""

import logging
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.models.dataset import Dataset, DatasetRelationship
from app.schemas.dataset import ColumnMeta
from app.services.retrieval.vector_store import ColumnVectorStore, VectorStoreError

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "by", "and", "or", "is", "are", "what",
    "show", "me", "with", "from", "my", "all", "per", "each", "how", "many", "much", "over",
    "last", "past", "total", "now", "it", "that", "this", "than", "compare", "between", "break",
    "down", "than", "please", "give", "get", "can", "you", "do", "does",
}
_RRF_K = 60
# Carried-over columns are a prior, not evidence: they rank below direct matches on the question.
_CONTEXT_WEIGHT = 0.5
_MAX_CONTEXT_COLUMNS = 5
_WIDE_TABLE_COLUMNS = 15

ColumnKey = tuple[str, str]  # (dataset_id, column)


@dataclass
class RetrievedDataset:
    dataset: Dataset
    columns: list[ColumnMeta]


@dataclass
class RetrievedSchema:
    datasets: list[RetrievedDataset]
    relationships: list[DatasetRelationship] = field(default_factory=list)
    vector_used: bool = False  # False when retrieval fell back to keywords only
    carried_over: list[ColumnKey] = field(default_factory=list)  # context columns that made the cut


def tokenize(text: str) -> set[str]:
    """Lowercase word tokens, minus stopwords, with a naive plural strip."""
    tokens = {t[:-1] if len(t) > 3 and t.endswith("s") else t for t in re.findall(r"[a-z0-9]+", text.lower())}
    return tokens - _STOPWORDS


class SchemaRetriever:
    """Ranks columns by keyword overlap and embedding similarity, fused with RRF."""

    def __init__(self, vector_store: ColumnVectorStore, top_k: int) -> None:
        self._vectors = vector_store
        self._top_k = top_k

    def retrieve(
        self,
        question: str,
        datasets: list[Dataset],
        relationships: list[DatasetRelationship],
        context_columns: Sequence[ColumnKey] = (),
    ) -> RetrievedSchema:
        """Select the schema relevant to `question`.

        `context_columns` are columns the previous answer used. They are fused in as a
        low-weight ranking so a follow-up such as "now by month" keeps its measure and
        dimension, while a question that clearly names other columns still outranks them.
        """
        if not datasets:
            return RetrievedSchema(datasets=[])

        keyword_ranked = self._keyword_rank(question, datasets)
        vector_ranked = self._vector_rank(question, datasets)
        context_ranked = self._context_rank(context_columns, datasets)
        top = self._fuse(
            [(keyword_ranked, 1.0), (vector_ranked, 1.0), (context_ranked, _CONTEXT_WEIGHT)]
        )[: self._top_k]

        chosen: dict[str, set[str]] = defaultdict(set)
        for dataset_id, column in top:
            chosen[dataset_id].add(column)
        # Datasets that join to a chosen dataset are needed for cross-file questions.
        for rel in relationships:
            if rel.left_dataset_id in chosen or rel.right_dataset_id in chosen:
                chosen[rel.left_dataset_id].add(rel.left_column)
                chosen[rel.right_dataset_id].add(rel.right_column)
        if not chosen:  # nothing matched: fall back to everything
            chosen = {d.id: set() for d in datasets}

        return RetrievedSchema(
            datasets=[self._select_columns(d, chosen[d.id]) for d in datasets if d.id in chosen],
            relationships=[
                r for r in relationships if r.left_dataset_id in chosen and r.right_dataset_id in chosen
            ],
            vector_used=bool(vector_ranked),
            carried_over=[key for key in top if key in set(context_ranked)],
        )

    @staticmethod
    def _select_columns(dataset: Dataset, wanted: set[str]) -> RetrievedDataset:
        columns = [ColumnMeta(**c) for c in dataset.columns]
        if len(columns) <= _WIDE_TABLE_COLUMNS or not wanted:
            return RetrievedDataset(dataset, columns)
        # For wide tables keep matches plus date columns (needed for time filters).
        kept = [c for c in columns if c.name in wanted or c.kind == "datetime"]
        return RetrievedDataset(dataset, kept)

    def _keyword_rank(self, question: str, datasets: list[Dataset]) -> list[ColumnKey]:
        query = tokenize(question)
        scored: list[tuple[float, ColumnKey]] = []
        for dataset in datasets:
            table_tokens = tokenize(dataset.table_name.replace("_", " "))
            for column in dataset.columns:
                name_tokens = tokenize(column["name"].replace("_", " "))
                sample_tokens = tokenize(" ".join(column.get("samples", [])))
                score = (
                    3 * len(query & name_tokens)
                    + 2 * len(query & sample_tokens)
                    + len(query & table_tokens)
                )
                if score:
                    scored.append((score, (dataset.id, column["name"])))
        return [key for _, key in sorted(scored, key=lambda item: -item[0])]

    @staticmethod
    def _context_rank(context_columns: Sequence[ColumnKey], datasets: list[Dataset]) -> list[ColumnKey]:
        """Keeps only context columns that still exist in the selected datasets."""
        available = {(d.id, c["name"]) for d in datasets for c in d.columns}
        return [key for key in context_columns if key in available][:_MAX_CONTEXT_COLUMNS]

    def _vector_rank(self, question: str, datasets: list[Dataset]) -> list[ColumnKey]:
        try:
            return self._vectors.query(question, [d.id for d in datasets], self._top_k * 2)
        except VectorStoreError as exc:
            logger.warning("vector retrieval unavailable, using keywords only: %s", exc)
            return []

    @staticmethod
    def _fuse(weighted_rankings: list[tuple[list[ColumnKey], float]]) -> list[ColumnKey]:
        """Weighted reciprocal rank fusion."""
        scores: dict[ColumnKey, float] = defaultdict(float)
        for ranking, weight in weighted_rankings:
            for rank, key in enumerate(ranking):
                scores[key] += weight / (_RRF_K + rank + 1)
        return sorted(scores, key=lambda key: -scores[key])
