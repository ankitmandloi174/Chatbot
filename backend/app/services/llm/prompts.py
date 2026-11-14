"""Prompt templates and schema/history rendering."""

from collections.abc import Sequence

from app.models.conversation import Message
from app.services.retrieval.retriever import RetrievedSchema

PLANNER_SYSTEM = """You are a data analysis planner. Given a user question, the available \
pandas DataFrames (schema below) and the conversation so far, produce an analysis plan.

Reply with ONE JSON object and nothing else, with these keys:
- "output_type": one of "text", "table", "chart", "mixed"
- "datasets": list of DataFrame variable names needed
- "steps": ordered list of short strings describing the pandas operations (filters, joins, \
groupbys, aggregations)
- "chart": null, or {"type": "line|bar|pie|scatter|histogram|box", "x": str, "y": str, "title": str}
- "assumptions": list of strings (e.g. how relative dates were interpreted)

Rules:
- Use only datasets and columns that appear in the schema.
- Choose "chart" or "mixed" for trends over time, comparisons across categories, or distributions.
- Relative dates ("past year", "last 6 months") are relative to the MAXIMUM date in the \
relevant date column, not today's date.
- For cross-file questions, use the listed join relationships.
- For follow-ups ("now break it down by category"), build on the previous analysis."""

CODEGEN_SYSTEM = """You are an expert pandas engineer. Write Python code that answers the question \
following the analysis plan.

Environment:
- Already available (do NOT import them): pd (pandas), np (numpy), px (plotly.express), \
go (plotly.graph_objects), and one DataFrame variable per dataset (names in the schema); \
they are also in the dict `dfs`.
- No file, network or OS access. No imports at all.
- Do not mutate the original DataFrames; work on copies.

Output contract:
- Assign the final computed answer to a variable named `result`: a DataFrame, Series or scalar. \
Keep DataFrame results to at most a few hundred rows (aggregate!).
- If a chart is useful, assign a Plotly figure to `fig` (built from the aggregated data, not raw rows).
- Never hard-code numbers; compute everything from the data.
- For month/quarter groupings prefer `dt.to_period("M").astype(str)` or `dt.strftime("%Y-%m")` so the \
labels are plain strings.

Reply with ONLY one ```python code block."""

REPAIR_ADDENDUM = """The previous code failed. Fix it.

Previous code:
```python
{code}
```

Error:
{error}

Return the corrected full code in one ```python block."""

EXPLAINER_SYSTEM = """You are a data analyst explaining computed results to a business user.
Write a concise answer (2-6 sentences, markdown allowed) based ONLY on the computed result below.
- Quote the real numbers from the result; never invent or estimate values.
- Mention relevant assumptions (e.g. date window used).
- If a chart or table accompanies the answer, refer to it naturally.
- If the result is empty, say so and suggest why."""


FOLLOW_UP_SYSTEM = """You suggest follow-up questions for a data analyst's last answer.
Write exactly 3 short, specific questions the user is likely to ask next. Rules:
- Base each question on something concrete in the COMPUTED RESULT (a top/bottom item, a gap, \
a trend, an unexpected value), or on a clearly different cut of the data.
- Use ONLY columns listed in the COLUMN CATALOG, and name each one in plain words in the question \
(for example the column `order_date` can be written as "order date").
- Never ask something that repeats, or only rewords, a question listed under ALREADY ASKED or \
ALREADY COVERED.
- No vague questions such as "tell me more" or "what else can I learn".
Reply with ONLY this JSON, where `columns` lists every catalog column the question relies on \
written as table.column:
{"suggestions": [{"question": "...", "columns": ["table.column"]}]}"""


def follow_up_user_prompt(
    question: str, result_text: str, used: str, catalog: str, asked: str, covered: str
) -> str:
    return (
        f"QUESTION JUST ANSWERED: {question}\n\nCOMPUTED RESULT:\n{result_text}\n\n"
        f"COLUMNS USED BY THE ANSWER: {used}\n\nCOLUMN CATALOG:\n{catalog}\n\n"
        f"ALREADY ASKED:\n{asked}\n\nALREADY COVERED:\n{covered}"
    )


def render_schema(schema: RetrievedSchema) -> str:
    """Render retrieved datasets/columns/relationships as prompt text."""
    lines: list[str] = []
    for item in schema.datasets:
        ds = item.dataset
        lines.append(f"DataFrame `{ds.table_name}` (file: {ds.name}, {ds.row_count} rows)")
        for col in item.columns:
            detail = f"nulls={col.null_count}, unique={col.unique_count}"
            if col.min is not None:
                detail += f", range=[{col.min} .. {col.max}]"
            if col.samples:
                detail += f", e.g. {col.samples}"
            lines.append(f"  - {col.name}: {col.dtype} ({col.kind}; {detail})")
    if schema.relationships:
        names = {i.dataset.id: i.dataset.table_name for i in schema.datasets}
        lines.append("Likely join keys:")
        for r in schema.relationships:
            lines.append(
                f"  - {names[r.left_dataset_id]}.{r.left_column} <-> "
                f"{names[r.right_dataset_id]}.{r.right_column} (value overlap {r.overlap:.0%})"
            )
    return "\n".join(lines)


def render_history(messages: Sequence[Message], max_turns: int) -> str:
    """Render recent turns, including the previous analysis plan/code for follow-ups."""
    recent = list(messages)[-max_turns * 2 :]
    if not recent:
        return "(no previous messages)"
    lines: list[str] = []
    for message in recent:
        lines.append(f"{message.role.upper()}: {message.content}")
        payload = message.payload or {}
        if message.role == "assistant" and payload.get("code"):
            lines.append(f"  [code used]\n{payload['code']}")
    return "\n".join(lines)


def planner_user_prompt(question: str, schema_text: str, history_text: str) -> str:
    return f"SCHEMA:\n{schema_text}\n\nCONVERSATION SO FAR:\n{history_text}\n\nQUESTION: {question}"


def codegen_user_prompt(question: str, plan_json: str, schema_text: str, history_text: str) -> str:
    return (
        f"SCHEMA:\n{schema_text}\n\nCONVERSATION SO FAR:\n{history_text}\n\n"
        f"ANALYSIS PLAN:\n{plan_json}\n\nQUESTION: {question}"
    )


def explainer_user_prompt(question: str, plan_json: str, result_text: str, schema_text: str) -> str:
    return (
        f"AVAILABLE SCHEMA:\n{schema_text}\n\nQUESTION: {question}\n\n"
        f"PLAN:\n{plan_json}\n\nCOMPUTED RESULT:\n{result_text}"
    )
