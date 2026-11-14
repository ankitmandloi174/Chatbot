from app.services.analysis.lineage import referenced_columns
from app.services.analysis.result_metrics import extract_kpis

TABLES = {"sales": ["region", "revenue", "order_date"], "targets": ["region", "target"]}


def test_lineage_lists_only_used_datasets_and_referenced_columns():
    code = "m = sales[sales['order_date'] > '2024-01-01']\nresult = m.groupby('region')['revenue'].sum()"
    assert referenced_columns(code, TABLES) == {"sales": ["region", "revenue", "order_date"]}


def test_lineage_handles_dfs_lookup_attributes_and_bad_code():
    assert referenced_columns("result = dfs['targets'].target.sum()", TABLES) == {"targets": ["target"]}
    assert referenced_columns("result = (", TABLES) == {}


def test_kpis_for_scalar_and_single_row_only():
    assert extract_kpis({"kind": "scalar", "value": 12.5}) == [{"label": "Result", "value": 12.5}]
    assert extract_kpis({"kind": "scalar", "value": "text"}) == []
    one_row = {"kind": "table", "columns": ["total", "name", "avg"], "rows": [[10, "x", 2.5]], "total_rows": 1}
    assert extract_kpis(one_row) == [{"label": "total", "value": 10}, {"label": "avg", "value": 2.5}]
    many = {"kind": "table", "columns": ["a"], "rows": [[1], [2]], "total_rows": 2}
    assert extract_kpis(many) == []
