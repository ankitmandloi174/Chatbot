"""End-to-end API tests with a fake LLM and the real sandbox."""

from fastapi.testclient import TestClient

from tests.conftest import SALES_CSV, TARGETS_CSV, FakeLLM, csv_file

GOOD_CODE = (
    "result = sales.groupby('region', as_index=False)['revenue'].sum()\n"
    "fig = px.bar(result, x='region', y='revenue')"
)


def _upload(client: TestClient, *files):
    return client.post("/api/datasets", files=list(files))


def test_upload_multiple_csvs_in_parallel_and_infer_relationship(client: TestClient):
    response = _upload(client, csv_file("sales.csv", SALES_CSV), csv_file("targets.csv", TARGETS_CSV))
    body = response.json()
    assert response.status_code == 200
    assert {d["table_name"] for d in body["datasets"]} == {"sales", "targets"}
    assert body["failures"] == []
    assert any(r["left_column"] == "region" for r in body["relationships"])
    assert len(client.get("/api/datasets").json()) == 2


def test_upload_reports_per_file_failures(client: TestClient):
    body = _upload(client, csv_file("notes.txt", "hi"), csv_file("sales.csv", SALES_CSV)).json()
    assert [f["filename"] for f in body["failures"]] == ["notes.txt"]
    assert len(body["datasets"]) == 1


def test_delete_dataset(client: TestClient):
    dataset_id = _upload(client, csv_file("sales.csv", SALES_CSV)).json()["datasets"][0]["id"]
    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 204
    assert client.get("/api/datasets").json() == []
    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 404


def test_chat_returns_text_table_chart_and_persists_follow_up_context(client: TestClient):
    _upload(client, csv_file("sales.csv", SALES_CSV))
    client.app.state.llm = FakeLLM(
        ["result = sales['nope']", GOOD_CODE],
        follow_ups=[
            {"question": "Why is revenue in North higher than in South by region?", "columns": ["sales.revenue", "sales.region"]},
            {"question": "What else can I learn?", "columns": ["sales.revenue"]},
            {"question": "Show profit by warehouse", "columns": ["sales.profit"]},
        ],
    )
    conversation_id = client.post("/api/conversations").json()["id"]

    reply = client.post(
        f"/api/conversations/{conversation_id}/messages", json={"question": "Revenue by region?"}
    ).json()
    assert reply["attempts"] == 2  # first attempt failed and was repaired
    assert reply["tables"][0]["columns"] == ["region", "revenue"]
    assert reply["charts"][0]["data"][0]["type"] == "bar"
    assert reply["content"].startswith("Total revenue is")
    assert "FOLLOW_UPS" not in reply["content"]
    # LLM ideas pass the gate only if specific and grounded; profile-based ones fill the rest.
    assert reply["followups"][:2] == [
        "Why is revenue in North higher than in South by region?",
        "Show the monthly trend of revenue",
    ]
    assert reply["followups"][2].startswith("Compare revenue for ")
    assert len(reply["followups"]) == 3
    assert reply["sources"] == [{"table_name": "sales", "file_name": "sales.csv", "columns": ["region", "revenue"]}]

    trace = reply["trace"]
    assert trace["retrieval_method"] in {"Keyword + vector search", "Keyword search only"}
    assert [(a["validation"], a["execution"]) for a in trace["attempts"]] == [
        ("passed", "failed"), ("passed", "passed"),
    ]
    assert "KeyError" in trace["attempts"][0]["error"]

    follow_up = client.post(
        f"/api/conversations/{conversation_id}/messages", json={"question": "Now by month"}
    ).json()
    assert {"sales.revenue", "sales.region"} <= set(follow_up["trace"]["carried_over"])
    detail = client.get(f"/api/conversations/{conversation_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert detail["title"] == "Revenue by region?"


def test_chat_without_datasets_is_a_bad_request(client: TestClient):
    client.app.state.llm = FakeLLM([GOOD_CODE])
    conversation_id = client.post("/api/conversations").json()["id"]
    response = client.post(f"/api/conversations/{conversation_id}/messages", json={"question": "hi"})
    assert response.status_code == 400


def test_chat_without_api_key_returns_503(client: TestClient):
    _upload(client, csv_file("sales.csv", SALES_CSV))
    conversation_id = client.post("/api/conversations").json()["id"]
    response = client.post(f"/api/conversations/{conversation_id}/messages", json={"question": "hi"})
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
