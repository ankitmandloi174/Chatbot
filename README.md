# CSV Chat Analyst

Chat with many CSV files at once. Ask questions in plain English and get an answer backed by **actually computed** results, plus tables and interactive charts when they help.

## Demo

<video src="working-demo.webm" controls muted width="100%">
  Your viewer cannot play embedded video.
</video>

[![Watch Demo](https://img.shields.io/badge/Watch-Demo-red?logo=github)](https://github.com/user-attachments/assets/6e748cf8-891f-4dc4-beef-d2731b40924c)



**Contents**

1. [Problem statement](#1-problem-statement)
2. [How the system works](#2-how-the-system-works)
3. [Setup and run](#3-setup-and-run)
4. [Libraries used and why](#4-libraries-used-and-why)
5. [How evaluation could be performed](#5-how-evaluation-could-be-performed)
6. [Known limitations](#6-known-limitations)

---

## 1. Problem statement

Business users keep data spread across several CSV files and have no quick way to ask questions of it:

- "What was total revenue last year?"
- "Show the sales trend over the last 6 months."
- "Compare regions across these two files."

Spreadsheets get slow and manual, and asking a plain chatbot is risky because language models invent numbers.

**This project lets a user upload many CSVs and ask questions conversationally, including follow-ups, while keeping the answers trustworthy:**

- The LLM never calculates anything itself. It writes pandas code, the code runs on the real data, and the explanation is written from that output.
- Every answer shows what it was based on: which files and columns were used, the generated code, and any errors along the way.
- No SQL or coding knowledge is needed from the user.

---

## 2. How the system works

### The big picture

```
UPLOAD
  CSV files ─► validate ─► clean ─► profile ─► save Parquet + SQLite + Chroma index ─► detect joins

QUESTION
  question ─► find relevant columns (keyword + vector search, only inside uploaded datasets)
           ─► LLM writes a plan (JSON) ─► LLM writes pandas code
           ─► safety check (AST) ─► run in a sandbox ──► error? send code + error back to the LLM (up to 3 retries)
           ─► result (table / number / chart) ─► LLM explains it ─► follow-up questions
           ─► everything saved in SQLite, so later questions can build on it
```

### Step by step

| Stage | What happens | Code |
|---|---|---|
| **Upload** | Several files are streamed to disk with a size limit and processed in parallel | `api/routes/datasets.py` |
| **Clean** | Column names become snake_case; types are inferred (`$1,200` becomes a number, text becomes dates or booleans); duplicate and empty rows are removed; missing values are handled (see policy below); outliers are **flagged, not removed** | `services/ingestion/cleaning.py` |
| **Profile** | Per column: type, kind, null count, distinct values, min, max, mean, sample values | `ingestion/metadata.py` |
| **Relationships** | Finds columns that can join two files, by related names plus overlapping values (`customer_id` in two files) | `ingestion/relationships.py` |
| **Retrieval** | Picks the columns relevant to the question: keyword scoring plus ChromaDB embeddings, merged with reciprocal rank fusion. Falls back to keywords only if the vector index is unavailable | `services/retrieval/` |
| **Plan, then code** | Two LLM calls: first a JSON analysis plan, then the pandas code | `services/analysis/`, `services/llm/` |
| **Validate** | The code is checked against an allow-list: no imports, file, network or OS access, no `eval`/`exec`/`open`, no dunder tricks | `analysis/code_validator.py` |
| **Execute** | The code runs in a separate Python subprocess with restricted builtins, blocked sockets, memory and CPU limits, a timeout and a clean environment (no API keys) | `analysis/sandbox*.py` |
| **Repair** | If validation or execution fails, the code and the error go back to the LLM (`MAX_CODE_RETRIES`, default 3). If it still fails, the user gets an honest failure message instead of an invented answer | `analysis/pipeline.py` |
| **Explain** | The LLM writes a short answer from the computed result, stating assumptions such as the date window | `analysis/explainer.py` |
| **Follow-ups** | Suggested next questions (see below) | `services/suggestions/` |
| **Persist** | The question, answer, tables, charts, code and execution trace are stored in SQLite | `conversation/chat_service.py` |

### Good to know

**Which data a question can see.** Every uploaded dataset is always in scope. Retrieval then narrows it down to the columns that matter for the question, and datasets that join to a chosen one are added automatically so cross-file questions work. To exclude a file, delete it from the sidebar.

**Where data is stored.** Everything lives under one data folder (`/data` in Docker, `./data` locally):

| Store | Holds |
|---|---|
| SQLite (`app.db`) | Datasets, join relationships, conversations and messages |
| Parquet files | The cleaned data; this is what the sandbox runs the pandas code on |
| ChromaDB | One embedding per column (name, type and sample values), used only to pick relevant columns |
| Raw folder | The original uploads |

**The LLM only sees the schema.** It gets column names, types, ranges and a few sample values, never the data rows.

**Conversation memory.** The last 6 turns (`HISTORY_TURNS`) are passed to the planner and code generator, including the code used for earlier answers, so "now break that down by region" can build on the previous analysis. Older turns are dropped, not summarised. Retrieval also carries over the columns used by the previous answer, with a lower weight, so short follow-ups keep their measure and dimension.

**Follow-up suggestions.** Each answer ends with up to 3 suggested next questions (`FOLLOW_UP_COUNT`):

1. *Profile-based*: built from real column names and values using a set of analytical moves (break it down, change the time window, rank, and so on). They are grounded by construction.
2. *Result-specific* (optional, `FOLLOW_UP_LLM_ENABLED`): one extra LLM call, run in parallel with the explanation, proposes questions about the actual result.
3. *Validation gate*: every candidate is dropped if it is vague, repeats an earlier question, or mentions columns outside the relevant datasets. If the LLM call fails, you simply get fewer suggestions.

**Missing-value policy (deliberately light).**
- Columns more than 90% empty are dropped.
- Text nulls become `"Unknown"`.
- Numeric nulls are median-filled only when they are 5% of values or fewer; otherwise they stay `NaN`, which pandas aggregations skip.
- Every change is recorded in a per-dataset cleaning report shown in the UI.

**Relative dates.** "Past year" and "last 6 months" are measured from the **latest date in the data**, not today's date, and the answer states this assumption.

### The user interface

Every answer is built from data the backend actually returned; nothing is mocked.

| Area | What it does |
|---|---|
| **Sidebar** (collapsible) | A "New chat" button; the **Datasets** section with a drag-and-drop CSV upload and one card per file (rows, columns, cleaning summary, column list, delete); the **Conversations** history; each part scrolls on its own, and the user card is pinned at the bottom |
| **Welcome screen** | Starter questions built in the browser from your real columns (`utils/suggestions.ts`), including a cross-file question when a join key was found |
| **Answer** | Markdown text, KPI cards (single-number or single-row results only), an interactive Plotly chart, and a sortable, paginated data table (10 rows per page) |
| **Data used** | The files and columns the generated code actually referenced, found by parsing the code (`analysis/lineage.py`) |
| **Execution details** | Retrieval method and columns, join keys, the plan, every code attempt, validation and execution outcomes with real errors and timings |
| **Follow-ups** | Pill buttons under the latest answer; clicking one asks it |
| **Composer** | Multi-line input, "Attach CSV" upload, Enter to send, Shift+Enter for a new line, 2,000-character limit (matches the API) |
| **Theme** | Light and dark follow the operating system; charts restyle to match |

### Project layout

```
backend/app/
  api/            thin routes + dependency providers
  core/           config (pydantic-settings), logging, exceptions
  db/ models/     SQLAlchemy engine and ORM models
  repositories/   data access
  schemas/        Pydantic request/response models
  services/
    ingestion/    load, clean, profile, relationships
    retrieval/    keyword + vector search
    llm/          providers and prompts
    analysis/     planner, code generator, validator, sandbox, explainer
    suggestions/  follow-up questions
    conversation/ chat turn orchestration and history
backend/tests/    pytest suite

frontend/src/
  components/     small presentational components
  hooks/          useDatasets, useChat, useSidebar, ...  (stateful logic)
  services/api.ts all HTTP calls
  styles/         design tokens and per-area CSS
  types/          TypeScript interfaces
```

---

## 3. Setup and run

### Prerequisites

- **Docker** (Option A), or **Python 3.10** and **Node 20** (Option B)
- An API key for one LLM provider

### Step 1: configure the LLM

```bash
cp .env.example .env
```

Then edit `.env`:

| Setting | Meaning |
|---|---|
| `LLM_PROVIDER` | `openai`, `gemini`, `openrouter` or `litellm` |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | The key for the provider you chose |
| `OPENAI_MODEL` / `GEMINI_MODEL` / `OPENROUTER_MODEL` | Optional model override (defaults are in `.env.example`) |
| `LITELLM_MODEL` | For `litellm`, any model string it supports, e.g. `anthropic/claude-sonnet-4-5` or `ollama/llama3`. `LITELLM_API_KEY` and `LITELLM_API_BASE` are optional |

No key is needed to start the app or upload data. Chat returns a clear 503 until the selected provider's key is set.

Other useful settings (all optional):

| Setting | Default | Meaning |
|---|---|---|
| `MAX_UPLOAD_MB` / `MAX_FILES_PER_UPLOAD` | 200 / 10 | Upload limits |
| `MAX_CODE_RETRIES` | 3 | Repair attempts after a failed analysis |
| `SANDBOX_TIMEOUT_SECONDS` / `SANDBOX_MEMORY_MB` | 60 / 4096 | Sandbox limits |
| `HISTORY_TURNS` | 6 | Past turns passed to the LLM |
| `RETRIEVAL_TOP_K` | 12 | Columns kept by retrieval |
| `RESULT_MAX_ROWS` | 1000 | Rows of a result sent to the browser |
| `FOLLOW_UP_COUNT` / `FOLLOW_UP_LLM_ENABLED` | 3 / true | Number of suggestions; extra LLM call for result-specific ones |

### Step 2: run it

#### Option A: Docker (simplest)

```bash
docker compose up --build
```

Open **http://localhost:3000**. nginx serves the UI and proxies `/api` to the backend. Your data (SQLite, Parquet, ChromaDB) is kept in the `app-data` volume, so it survives restarts.

#### Option B: local development

```bash
# Terminal 1: backend
cd backend
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:create_app --factory --reload --port 8000   # reads ../.env

# Terminal 2: frontend
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to port 8000
```

### Try it

1. Upload one or more CSVs by dragging them onto the sidebar.
2. Click a starter question, or type your own, for example *"Which months had the highest sales, and is there a seasonal trend?"*
3. Open "Execution details" on an answer to see exactly how it was computed.

### Tests

```bash
cd backend && source .venv/bin/activate && pytest   # no API key needed
cd frontend && npm run build                         # type-checks and builds
```

The backend tests use a scripted fake LLM, while the sandbox, ingestion, retrieval and API layers run for real.

### Troubleshooting

| Problem | Fix |
|---|---|
| `401 Unauthorized` while Docker pulls images | Saved Docker Hub credentials are stale. Run `docker logout` (the images are public) or `docker login` again |
| Chat shows a 503 error | The API key for `LLM_PROVIDER` is missing in `.env` |
| After editing code, the Docker app looks unchanged | Rebuild with `docker compose up -d --build` |

### API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/datasets` | Upload many CSVs (multipart) |
| GET | `/api/datasets` | List datasets |
| DELETE | `/api/datasets/{id}` | Remove a dataset |
| GET | `/api/datasets/relationships` | Inferred join keys |
| POST / GET | `/api/conversations` | Create / list conversations |
| GET / DELETE | `/api/conversations/{id}` | Read history / delete |
| POST | `/api/conversations/{id}/messages` | Ask a question |

Interactive docs: http://localhost:8000/docs when running locally.

---

## 4. Libraries used and why

### Backend

| Library | Why |
|---|---|
| FastAPI, Pydantic, pydantic-settings | Typed, thin routes; validated request and response models; configuration from `.env` |
| pandas, numpy, pyarrow | Cleaning and analysis; Parquet gives fast reloads and typed column storage for large files |
| LangChain (`langchain-openai`, `langchain-google-genai`) | One interface over OpenAI, Gemini and OpenRouter (OpenAI-compatible) |
| LiteLLM | Optional provider: one call interface for 100+ hosted and local models (Anthropic, Azure, Ollama, and more) |
| ChromaDB | Local persistent vector index of column descriptions; uses its built-in ONNX MiniLM embeddings, so no extra API is needed |
| SQLAlchemy + SQLite | Datasets, relationships and conversations with no extra service to run |
| Plotly | The generated code builds charts server-side as Plotly figures |
| pytest, httpx | Backend tests |

### Frontend

| Library | Why |
|---|---|
| React + TypeScript + Vite | Small, typed single-page app with fast builds |
| plotly.js-dist-min + react-plotly.js | Renders the interactive charts; lazy-loaded because the library is large |
| react-markdown + remark-gfm | Safe Markdown (lists, tables, code) for answers; raw HTML is not rendered |

The UI uses no component library. Styling is plain CSS with design tokens, and the icons are inline SVGs, which keeps dependencies low.

---

## 5. How evaluation could be performed

This is a plan for measuring quality. The repo's tests cover the safety and pipeline pieces; the golden-set, load and faithfulness checks below are not automated yet.

### Accuracy of the AI-generated insights

- **Golden set.** Build datasets with known answers (reference values from hand-written pandas or SQL) and 50 to 200 questions: aggregations, filters, group-bys, time windows, cross-file joins and follow-ups. Score *execution accuracy* (the computed value matches the reference within a tolerance), whether the chart type fits, and whether the explanation quotes the computed numbers.
- **Faithfulness check.** Automatically verify that every number in the explanation appears in the computed result (regex plus tolerance) and flag any invented figures. An LLM-as-judge can grade clarity, backed by a human spot check.
- **Component metrics.** Retrieval recall@k (are the columns the reference solution needs retrieved?), plan validity rate, first-attempt code success rate, average retries, and final failure rate.
- **Regression runs.** Run the golden set on every prompt or model change and track pass rate by question category.

### Performance on large datasets

- **Synthetic data.** Generate CSVs of 1M, 10M and 50M rows, tables with 200+ columns, and many files at once. Measure upload and cleaning time, Parquet size, peak memory, per-stage latency (retrieval, LLM calls, sandbox, serialisation) and end-to-end p50/p95.
- **Load tests.** Use Locust or k6 for concurrent uploads and questions, to size the upload thread pool and find sandbox memory limits and timeouts.
- **Payload limits.** Confirm that chart data is aggregated and tables are capped at `RESULT_MAX_ROWS`, so response size stays bounded however large the input is.

### Edge cases and robustness

- **Data.** Empty and header-only files, non-UTF-8 encodings, odd delimiters, duplicate, blank or unicode column names, mixed-type and all-null columns, currency and percent strings, ambiguous date formats, high-cardinality categories, duplicate file names and re-uploads of the same file.
- **Questions.** Ambiguous or unanswerable questions (columns that don't exist), empty results, joins with no shared key, follow-ups that refer to earlier results, and prompt-injection text inside CSV cells or questions.
- **Safety.** A corpus of malicious generated code (imports, `__class__` escapes, file and network access, infinite loops, memory bombs) that must all be rejected or contained. The unit tests include a starter set.
- **Resilience.** LLM timeouts, invalid JSON, a missing API key, an unavailable vector store (keyword fallback), and retry exhaustion, which must return an honest failure message rather than a fabricated answer.

---

## 6. Known limitations

- **The sandbox is proof-of-concept grade.** AST validation, restricted builtins, resource limits, blocked sockets and a clean environment stop accidental and common malicious behaviour, but a subprocess is not a hardened jail. For production, use gVisor, nsjail, Firecracker or a per-execution container with no network.
- **Single user, no authentication.** Datasets and conversations are global. The name in the sidebar footer is static.
- **No duplicate detection.** Uploading the same CSV twice creates a second dataset, a second set of embeddings and join relationships between the copies. Delete the extra copy from the sidebar.
- **Memory.** The LLM only sees the schema and samples, and files are stored as Parquet, but a CSV is read into memory once at upload and each analysis loads the datasets it needs. Beyond available RAM you would move to DuckDB or Polars lazy scans.
- **History is a sliding window.** Turns older than `HISTORY_TURNS` are dropped rather than summarised.
- **Answers are not streamed.** The reply appears in one piece after the analysis finishes.
- **Schema changes need a migration.** Tables are created at startup with `create_all`, so changing a model does not alter existing tables.
