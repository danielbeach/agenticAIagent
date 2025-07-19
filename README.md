# LangGraph Multi‑Agent Docker Example

A self‑contained demonstration of a **supervisor‑routed multi‑agent workflow** built with **LangGraph** + **LangChain**. It spins up:

1. **Postgres** (seeded sample `transactions` table)
2. **App container** running a LangGraph graph with three worker agents:

   * `SQL_AGENT` – queries Postgres through an LLM‑generated SQL tool
   * `WEB_AGENT` – performs DuckDuckGo search + optional page fetch
   * `SYNTHESIZER` – composes final answer
3. A **Supervisor (controller)** node that decides which agent acts next and when to finish (pattern from LangGraph multi‑agent tutorials).

The example objective (modifiable) asks for **structured spending insights + a current external headline**, forcing cross‑agent collaboration.

---

## Features

* **Supervisor routing** with conditional edges (state machine) selecting next agent or finishing.
* **Specialized worker prompts** enforcing domain focus & minimal hallucination.
* **Postgres SQL tool** via `QuerySQLDatabaseTool` (LLM generates SQL) seeded with realistic rows.
* **Web search + fetch** tools using DuckDuckGo (no API key required) and simple HTML extraction.
* **Pluggable architecture** – add new agents by registering a factory and updating the supervisor prompt.
* **Deterministic-ish control** (temperature 0 on supervisor) and creative synthesis (slightly higher temperature worker).
* **Docker Compose one‑command startup**.

---

## High‑Level Architecture

```
          +------------------+
          |    SUPERVISOR    |
          | (decide next)    |
          +---------+--------+
                    | (route: SQL_AGENT / WEB_AGENT / SYNTHESIZER / FINISH)
      +-------------+--------------+
      |                            |
+-----v------+              +------v------+             +--------------+
|  SQL_AGENT |              |  WEB_AGENT  |             | SYNTHESIZER  |
|  (DB SQL)  |              | (search+fx) |             | (final blend) |
+-----+------+              +------+------+
      |                            |
      +-------------+--------------+
                    |
               (back to)
               SUPERVISOR  --> FINISH
```

---

## Repository Layout

```
.
├── docker-compose.yml
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py          # Environment & model settings
│   ├── tools.py           # SQL & web tools
│   ├── agents.py          # Worker agent constructors & prompts
│   ├── memory.py          # Lightweight conversation state
│   ├── graph.py           # LangGraph build (state + nodes + edges)
│   └── run.py             # Entry point (sets objective & streams graph)
└── postgres/
    ├── Dockerfile
    └── init.sql           # Schema + seed data
```

---

## Data Model (Seeded)

`transactions(user_id INT, amount NUMERIC, category TEXT, ts TIMESTAMP)` – a handful of rows allowing basic aggregates (SUM, GROUP BY category, etc.).

---

## Prerequisites

* Docker & Docker Compose (Compose V2 recommended)
* An **OpenAI API key** (for `ChatOpenAI` & embeddings) exported as `OPENAI_API_KEY`

> *If you want to substitute another provider (e.g. Anthropic, Azure OpenAI), adjust `run.py` / model config accordingly.*

---

## Quick Start

```bash
# 1. Clone repo (after you create files from snippets)
export OPENAI_API_KEY=sk-...  # your key

# 2. Launch stack
docker compose up --build

# 3. Watch logs (should show supervisor decisions and agent outputs)
# 4. Edit app/run.py 'objective' variable; re-run container or `docker compose restart app`.
```

When finished: `docker compose down -v` (drops volumes & containers).

---

## Configuration

Environment variables consumed (see `docker-compose.yml` / `config.py`):

| Variable          | Purpose                                     | Default                                                   |
| ----------------- | ------------------------------------------- | --------------------------------------------------------- |
| `OPENAI_API_KEY`  | LLM auth                                    | (required)                                                |
| `OPENAI_MODEL`    | Chat model for supervisor/workers           | `gpt-4o-mini`                                             |
| `DATABASE_URL`    | SQLAlchemy URI inside container             | `postgresql+psycopg2://agent:agentpass@db:5432/analytics` |
| `SEARCH_PROVIDER` | (Placeholder for alternate search backends) | `duckduckgo`                                              |
| `MAX_TOKENS`      | (Not currently enforced; hook for future)   | `4096`                                                    |

Adjust `OPENAI_MODEL` for cost/performance tradeoffs.

---

## How It Works

1. **Supervisor Entry** – Graph entry point is `supervisor`, which inspects conversation state + objective.
2. **Decision** – Supervisor LLM outputs either an agent name or a termination marker (interpreted as FINISH).
3. **Worker Execution** – Selected worker runs via its `AgentExecutor` with only its allowed tools.
4. **Conversation Update** – Worker output appended to shared state.
5. **Loop** – Control returns to supervisor until it selects `SYNTHESIZER` and then finishes, or decides it already has enough context.

The `SYNTHESIZER` agent integrates prior SQL + web outputs into the final narrative.

---

## Running a Different Query

Edit in `app/run.py`:

```python
objective = "Provide a brief spending summary from transactions plus a current related market headline."
```

Example alternatives:

* Only structured: `"Summarize total spend per user and top categories."` (expect only `SQL_AGENT` + `SYNTHESIZER`)
* Web heavy: `"Give me a recent fintech headline and relate it to our internal spending data."` (expect `WEB_AGENT`, maybe `SQL_AGENT`, then `SYNTHESIZER`)

Restart container after edit.

---

## Extending the Graph

| Goal                       | Change                                                                                                      |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Add Vector Retrieval Agent | Implement a `vector_tool`; create `VECTOR_AGENT` factory; update supervisor prompt to list it.              |
| Add Critic Loop            | Introduce `CRITIC` agent returning quality feedback; supervisor chooses between `CRITIC` and `SYNTHESIZER`. |
| Limit Steps                | Wrap stream consumption with a step counter & abort after N transitions.                                    |
| Observability              | Integrate LangSmith tracing by setting `LANGCHAIN_TRACING_V2=true` & `LANGCHAIN_API_KEY`.                   |
| Caching                    | Memoize tool outputs (SQL query hash, search query) in a lightweight in‑memory dict or Redis.               |
| Guardrails                 | Add a safety agent or a SQL sanitizer (restrict schema, block DDL).                                         |

---

## Security & Safety Considerations

* **Read‑only DB user** recommended (current example uses default credentials; update for real use).
* Add explicit schema mention & allowlist columns to minimize risky SQL generation.
* Limit web fetch content size; sanitize / strip potentially unsafe HTML before passing back to LLM.
* Introduce rate limiting for search & fetch tools.
* Log supervisor decisions for auditability; consider structured JSON logs.

---

## Troubleshooting

| Symptom                       | Cause                                | Fix                                                                      |
| ----------------------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| `Could not connect to DB`     | Postgres not healthy yet             | Compose healthcheck waits; re-run or increase retries.                   |
| `SQL tool hallucinated table` | Missing schema context               | Add table DDL description into SQL agent system prompt.                  |
| Web search empty              | Rate limit / network issue           | Retry; change query; ensure outbound network allowed.                    |
| Infinite loop suspicion       | Supervisor keeps choosing same agent | Add step counter cap; refine supervisor prompt with completion criteria. |
| High token usage              | Long conversation context            | Truncate or summarize messages each cycle.                               |

---

## Roadmap Ideas

* Vector memory agent (Chroma / PGVector)
* Structured supervisor output (Pydantic) for deterministic routing
* Streaming partial outputs
* Automatic evaluation & confidence scoring
* FastAPI service exposing `/query` endpoint
* Test harness (pytest) with mocked LLM for deterministic CI

---
