from types import SimpleNamespace

from app.services.conversation.context import previous_columns


def _msg(role: str, payload: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(role=role, payload=payload)


def _sources(table: str, *columns: str) -> dict:
    return {"sources": [{"table_name": table, "file_name": f"{table}.csv", "columns": list(columns)}]}


DATASETS = [SimpleNamespace(id="d1", table_name="sales"), SimpleNamespace(id="d2", table_name="targets")]


def test_uses_only_the_most_recent_successful_answer():
    history = [
        _msg("assistant", _sources("sales", "old_col")),
        _msg("user"),
        _msg("assistant", _sources("sales", "revenue", "region")),
        _msg("user"),
        _msg("assistant", {"error": "boom", **_sources("sales", "broken")}),
    ]
    assert previous_columns(history, DATASETS) == [("d1", "revenue"), ("d1", "region")]


def test_empty_when_no_answer_has_sources():
    assert previous_columns([_msg("user"), _msg("assistant", {})], DATASETS) == []
    assert previous_columns([], DATASETS) == []


def test_drops_datasets_that_are_no_longer_selected():
    history = [_msg("assistant", {"sources": _sources("sales", "revenue")["sources"]
                                  + _sources("removed", "x")["sources"]})]
    assert previous_columns(history, DATASETS) == [("d1", "revenue")]
