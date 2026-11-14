"""Builds the follow-up context from one answered turn."""

from collections.abc import Sequence

from app.models.conversation import Message
from app.models.dataset import Dataset, DatasetRelationship
from app.schemas.chat import SourceOut
from app.schemas.dataset import ColumnMeta
from app.services.analysis.explainer import result_to_text
from app.services.analysis.models import ExecutionResult
from app.services.suggestions.models import ColumnRef, FollowUpContext, JoinKey, TableProfile


def _profile(dataset: Dataset) -> TableProfile:
    report = dataset.cleaning_report or {}
    return TableProfile(
        table_name=dataset.table_name,
        file_name=dataset.name,
        row_count=dataset.row_count,
        columns=tuple(ColumnMeta(**c) for c in dataset.columns),
        missing=report.get("missing_left", {}),
        outliers=report.get("outliers_flagged", {}),
    )


def build_follow_up_context(
    question: str,
    datasets: Sequence[Dataset],
    relationships: Sequence[DatasetRelationship],
    sources: Sequence[SourceOut],
    execution: ExecutionResult,
    history: Sequence[Message],
) -> FollowUpContext:
    """Snapshot into plain data so suggestions can be computed on a worker thread."""
    tables = {d.id: d.table_name for d in datasets}
    result = execution.result
    return FollowUpContext(
        question=question,
        profiles=tuple(_profile(d) for d in datasets),
        used=tuple(ColumnRef(s.table_name, column) for s in sources for column in s.columns),
        joins=tuple(
            JoinKey(
                ColumnRef(tables[r.left_dataset_id], r.left_column),
                ColumnRef(tables[r.right_dataset_id], r.right_column),
            )
            for r in relationships
            if r.left_dataset_id in tables and r.right_dataset_id in tables
        ),
        result_text=result_to_text(execution),
        result_rows=result["total_rows"] if result["kind"] == "table" else None,
        previous_questions=tuple(m.content for m in history if m.role == "user"),
    )
