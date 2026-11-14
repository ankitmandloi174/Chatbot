"""Derives retrieval context from earlier turns of a conversation."""

from collections.abc import Sequence

from app.models.conversation import Message
from app.models.dataset import Dataset
from app.services.retrieval.retriever import ColumnKey


def previous_columns(history: Sequence[Message], datasets: Sequence[Dataset]) -> list[ColumnKey]:
    """Columns used by the most recent successful answer, as `(dataset_id, column)` keys.

    Only the last answer counts so that stale topics do not accumulate. Failed answers
    are skipped because their code may reference columns that do not exist. Columns of
    datasets that are no longer selected are dropped.
    """
    ids_by_table = {d.table_name: d.id for d in datasets}
    for message in reversed(history):
        payload = message.payload or {}
        if message.role != "assistant" or payload.get("error") or not payload.get("sources"):
            continue
        return [
            (ids_by_table[source["table_name"]], column)
            for source in payload["sources"]
            if source["table_name"] in ids_by_table
            for column in source["columns"]
        ]
    return []
