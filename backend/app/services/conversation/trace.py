"""Builds the transparency data (trace + sources) stored with each answer."""

from app.schemas.chat import (
    AttemptTrace,
    ExecutionTrace,
    RelationshipTrace,
    RetrievedDatasetTrace,
    SourceOut,
)
from app.services.analysis.lineage import referenced_columns
from app.services.analysis.models import AnalysisOutcome
from app.services.retrieval.retriever import RetrievedSchema


def build_trace(
    schema: RetrievedSchema,
    outcome: AnalysisOutcome,
    retrieval_ms: int,
    explain_ms: int,
) -> ExecutionTrace:
    names = {item.dataset.id: item.dataset.table_name for item in schema.datasets}
    return ExecutionTrace(
        retrieval_method="Keyword + vector search" if schema.vector_used else "Keyword search only",
        carried_over=[f"{names[dataset_id]}.{column}" for dataset_id, column in schema.carried_over],
        retrieved=[
            RetrievedDatasetTrace(
                table_name=item.dataset.table_name,
                file_name=item.dataset.name,
                columns=[c.name for c in item.columns],
                total_columns=item.dataset.column_count,
            )
            for item in schema.datasets
        ],
        relationships=[
            RelationshipTrace(
                left=f"{names[r.left_dataset_id]}.{r.left_column}",
                right=f"{names[r.right_dataset_id]}.{r.right_column}",
                overlap=r.overlap,
            )
            for r in schema.relationships
        ],
        attempts=[AttemptTrace(**a.model_dump()) for a in outcome.attempt_log],
        retrieval_ms=retrieval_ms,
        planning_ms=outcome.planning_ms,
        explain_ms=explain_ms,
    )


def build_sources(schema: RetrievedSchema, outcome: AnalysisOutcome) -> list[SourceOut]:
    """Datasets/columns referenced by the final generated code."""
    loaded = set(outcome.loaded_datasets)
    items = [i for i in schema.datasets if i.dataset.table_name in loaded]
    used = referenced_columns(
        outcome.code, {i.dataset.table_name: [c["name"] for c in i.dataset.columns] for i in items}
    )
    return [
        SourceOut(table_name=i.dataset.table_name, file_name=i.dataset.name, columns=used[i.dataset.table_name])
        for i in items
        if i.dataset.table_name in used
    ]
