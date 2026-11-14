from types import SimpleNamespace

import pandas as pd

from app.schemas.dataset import ColumnMeta
from app.services.ingestion.metadata import build_column_metadata
from app.services.ingestion.relationships import DatasetRef, infer_relationships
from app.services.retrieval.retriever import SchemaRetriever, tokenize
from app.services.retrieval.vector_store import VectorStoreError


def _ref(tmp_path, name: str, frame: pd.DataFrame) -> DatasetRef:
    path = tmp_path / f"{name}.parquet"
    frame.to_parquet(path)
    return DatasetRef(name, str(path), build_column_metadata(frame))


def test_infers_join_on_shared_region_column(tmp_path):
    sales = _ref(tmp_path, "sales", pd.DataFrame({"region": ["N", "S", "E"] * 3, "revenue": range(9)}))
    targets = _ref(tmp_path, "targets", pd.DataFrame({"region": ["N", "S", "E"], "target": [1, 2, 3]}))
    found = infer_relationships(targets, [sales])
    assert [(r.left_column, r.right_column) for r in found] == [("region", "region")]


def test_no_relationship_for_unrelated_small_integers(tmp_path):
    a = _ref(tmp_path, "a", pd.DataFrame({"qty": [1, 2, 3, 1, 2]}))
    b = _ref(tmp_path, "b", pd.DataFrame({"rating": [1, 2, 3, 4, 5]}))
    assert infer_relationships(a, [b]) == []


class _DownVectors:
    def query(self, *_):
        raise VectorStoreError("offline")


def _dataset(table: str, columns: list[ColumnMeta]) -> SimpleNamespace:
    return SimpleNamespace(
        id=table, table_name=table, name=f"{table}.csv", row_count=10,
        columns=[c.model_dump() for c in columns],
    )


def _col(name: str, kind: str = "categorical", samples=()) -> ColumnMeta:
    return ColumnMeta(name=name, dtype="object", kind=kind, null_count=0, unique_count=3, samples=list(samples))


def test_keyword_retrieval_works_when_vector_store_is_down():
    sales = _dataset("sales", [_col("region", samples=["North"]), _col("revenue", "numeric")])
    people = _dataset("employees", [_col("department"), _col("salary", "numeric")])
    retriever = SchemaRetriever(_DownVectors(), top_k=5)
    schema = retriever.retrieve("total revenue by region", [sales, people], [])
    assert [d.dataset.table_name for d in schema.datasets] == ["sales"]


def test_tokenize_drops_stopwords_and_plurals():
    assert tokenize("What are the total sales by regions?") == {"sale", "region"}


def _wide_sales_and_customers():
    sales = _dataset("sales", [_col(f"metric_{i}", "numeric") for i in range(14)]
                     + [_col("revenue", "numeric"), _col("region")])
    customers = _dataset("customers", [_col("segment", samples=["Gold"]), _col("age", "numeric")])
    return sales, customers


def _kept(schema, table):
    return {c.name for item in schema.datasets if item.dataset.table_name == table for c in item.columns}


def test_follow_up_without_column_names_keeps_previous_columns():
    sales, customers = _wide_sales_and_customers()
    retriever = SchemaRetriever(_DownVectors(), top_k=5)
    carried = [("sales", "revenue"), ("sales", "region")]

    schema = retriever.retrieve("now by month", [sales, customers], [], context_columns=carried)

    assert {"revenue", "region"} <= _kept(schema, "sales")
    assert schema.carried_over == carried


def test_clear_topic_switch_outranks_carried_columns():
    sales, customers = _wide_sales_and_customers()
    retriever = SchemaRetriever(_DownVectors(), top_k=1)

    schema = retriever.retrieve(
        "which customer segment is biggest", [sales, customers], [],
        context_columns=[("sales", "revenue"), ("sales", "region")],
    )

    assert [d.dataset.table_name for d in schema.datasets] == ["customers"]
    assert schema.carried_over == []


def test_context_columns_that_no_longer_exist_are_ignored():
    sales, customers = _wide_sales_and_customers()
    retriever = SchemaRetriever(_DownVectors(), top_k=5)

    schema = retriever.retrieve(
        "now by month", [sales], [], context_columns=[("sales", "deleted_col"), ("gone", "revenue")]
    )

    assert schema.carried_over == []
