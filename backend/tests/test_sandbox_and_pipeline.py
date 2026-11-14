from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from app.services.analysis.code_generator import CodeGenerator
from app.services.analysis.pipeline import AnalysisPipeline
from app.services.analysis.planner import AnalysisPlanner
from app.services.analysis.sandbox import ExecutionError, SandboxExecutor
from tests.conftest import FakeLLM


@pytest.fixture
def dataset(tmp_path: Path) -> SimpleNamespace:
    path = tmp_path / "sales.parquet"
    pd.DataFrame({"region": ["N", "S", "N"], "revenue": [10.0, 20.0, 30.0]}).to_parquet(path)
    return SimpleNamespace(table_name="sales", parquet_path=str(path))


@pytest.fixture
def executor() -> SandboxExecutor:
    return SandboxExecutor(timeout_seconds=30, memory_mb=4096, max_rows=100)


def test_runs_code_and_returns_table_and_figure(executor, dataset):
    code = (
        "result = sales.groupby('region', as_index=False)['revenue'].sum()\n"
        "fig = px.bar(result, x='region', y='revenue')"
    )
    out = executor.run(code, [dataset])
    assert out.result["kind"] == "table"
    assert out.result["rows"] == [["N", 40.0], ["S", 20.0]]
    assert out.figure and out.figure["data"][0]["type"] == "bar"


def test_period_columns_serialize_in_table_and_figure(executor, tmp_path):
    path = tmp_path / "orders.parquet"
    pd.DataFrame(
        {"order_date": pd.to_datetime(["2024-01-05", "2024-01-20", "2024-02-03"]), "total": [1.0, 2.0, 4.0]}
    ).to_parquet(path)
    orders = SimpleNamespace(table_name="orders", parquet_path=str(path))
    code = (
        "df = orders.assign(month=orders['order_date'].dt.to_period('M'))\n"
        "monthly = df.groupby('month')['total'].sum().reset_index()\n"
        "fig = px.line(monthly, x='month', y='total')\n"
        "result = monthly"
    )
    out = executor.run(code, [orders])
    assert out.result["rows"] == [["2024-01", 3.0], ["2024-02", 4.0]]
    assert list(out.figure["data"][0]["x"]) == ["2024-01", "2024-02"]


def test_period_index_serializes(executor, tmp_path):
    path = tmp_path / "orders.parquet"
    pd.DataFrame({"order_date": pd.to_datetime(["2024-01-05", "2024-02-03"]), "total": [1.0, 4.0]}).to_parquet(path)
    orders = SimpleNamespace(table_name="orders", parquet_path=str(path))
    out = executor.run(
        "result = orders.set_index(orders['order_date'].dt.to_period('M'))['total']", [orders]
    )
    assert [row[0] for row in out.result["rows"]] == ["2024-01", "2024-02"]


def test_scalar_result(executor, dataset):
    assert executor.run("result = float(sales['revenue'].sum())", [dataset]).result == {
        "kind": "scalar", "value": 60.0,
    }


def test_runtime_error_reports_offending_line(executor, dataset):
    with pytest.raises(ExecutionError, match=r"(?s)KeyError.*line 2"):
        executor.run("x = 1\nresult = sales['missing']", [dataset])


def test_import_and_network_blocked_even_if_validation_skipped(executor, dataset):
    with pytest.raises(ExecutionError, match="not allowed"):
        executor.run("import os\nresult = 1", [dataset])
    with pytest.raises(ExecutionError):
        executor.run("result = pd.io.common.urlopen('http://example.com')", [dataset])


def test_timeout(dataset):
    slow = SandboxExecutor(timeout_seconds=2, memory_mb=4096, max_rows=10)
    with pytest.raises(ExecutionError):
        slow.run("while True:\n    pass\nresult = 1", [dataset])


def _pipeline(llm: FakeLLM, executor: SandboxExecutor, retries: int = 3) -> AnalysisPipeline:
    return AnalysisPipeline(AnalysisPlanner(llm), CodeGenerator(llm), executor, retries)


def test_pipeline_retries_after_failure_then_succeeds(executor, dataset):
    llm = FakeLLM(["result = sales['nope']", "result = float(sales['revenue'].sum())"])
    outcome = _pipeline(llm, executor).run("total?", [dataset], "schema", "history")
    assert outcome.error is None
    assert outcome.attempts == 2
    assert outcome.execution.result["value"] == 60.0


def test_pipeline_gives_up_after_max_retries(executor, dataset):
    llm = FakeLLM(["result = sales['nope']"])
    outcome = _pipeline(llm, executor, retries=2).run("total?", [dataset], "schema", "history")
    assert outcome.execution is None
    assert outcome.attempts == 3
    assert "KeyError" in outcome.error
    assert llm.codegen_calls == 3
