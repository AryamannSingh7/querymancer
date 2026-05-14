<div align="center">

# Querymancer

### Conversational analytics over multi-schema databases

**Ask a database in plain English. Get safe SQL, live results, and the right chart back — with retrieval-augmented schema context, an agentic self-correction loop, and a Gemini-primary / Groq-fallback LLM strategy that keeps the system answering through free-tier quota walls.**

<p>
  <a href="https://querymancer.vercel.app"><img alt="Live demo" src="https://img.shields.io/badge/live%20demo-querymancer.vercel.app-c5f500?style=for-the-badge&logo=vercel&logoColor=000000&labelColor=000000"></a>
  <a href="https://asinghby-querymancer-backend.hf.space/docs"><img alt="API" src="https://img.shields.io/badge/api-hf%20space-FFD21E?style=for-the-badge&logo=huggingface&logoColor=000000&labelColor=000000"></a>
  <a href="docs/architecture.md"><img alt="Architecture" src="https://img.shields.io/badge/architecture-docs-7c3aed?style=for-the-badge&labelColor=000000"></a>
</p>

<p>
  <img alt="backend ci" src="https://img.shields.io/github/actions/workflow/status/AryamannSingh7/querymancer/backend-ci.yml?branch=main&label=backend%20ci&style=flat-square&logo=github&labelColor=222">
  <img alt="frontend ci" src="https://img.shields.io/github/actions/workflow/status/AryamannSingh7/querymancer/frontend-ci.yml?branch=main&label=frontend%20ci&style=flat-square&logo=github&labelColor=222">
  <img alt="python" src="https://img.shields.io/badge/python-3.11-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=222">
  <img alt="next.js" src="https://img.shields.io/badge/next.js-16-000?style=flat-square&logo=nextdotjs&labelColor=222">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-c5f500?style=flat-square&labelColor=222">
</p>

<br/>

<img src="querymancer-desktop-final.png" alt="Querymancer desktop UI" width="900"/>

</div>

<br/>

## Highlights

|  |  |  |
|---|---|---|
| **RAG over schema** | **Agentic self-correction** | **Defense-in-depth safety** |
| Top-K pgvector retrieval surfaces only the tables that matter, so 13-table databases don't blow the prompt window. Asymmetric `task_type` (DOCUMENT vs QUERY) and 768-d MRL-renormalised vectors. | When generated SQL fails to execute, the verbatim DB error is fed back into the next attempt (max 3). Most failures fix themselves on attempt 2 — streamed live to the frontend as it happens. | Two independent layers: `sqlglot` AST + denylist + single-statement + auto-`LIMIT`, *and* the connection itself opens `mode=ro`. Layer 1 can't be bypassed by stacked-statement or comment-injection tricks. |
| **Gemini → Groq fallback** | **Multi-turn refinement** | **Production-grade eval** |
| When Gemini's free-tier daily cap hits, `llm.generate_sql` automatically retries the same prompt against Groq Llama 3.3 70B. The demo stays live on quota days. | Sessions persist to Supabase; the last 2 turns get inlined into the prompt. Ask *"now break that down by category"* and the model resolves the pronoun against the previous SQL. | 150-case async eval harness grades by row-count assertion across 3 DBs and 3 difficulty tiers. Writes dated markdown reports incrementally — Ctrl-C leaves a valid partial. |

<br/>

## Architecture

```mermaid
flowchart LR
    UI["Next.js<br/>(Vercel)"] -- "/backend/* proxy" --> API["FastAPI<br/>(HF Spaces)"]
    API --> AGENT["Agent loop<br/>(max 3 attempts)"]
    AGENT -- "top-K=5" --> RAG[("Supabase pgvector<br/>schema_embeddings")]
    AGENT --> LLM["llm.generate_sql"]
    LLM --> GEM["Gemini 2.5 Flash"]
    LLM -. "429 / 5xx" .-> GROQ["Groq Llama 3.3 70B"]
    AGENT --> SAFE["sqlglot AST<br/>+ denylist<br/>+ LIMIT"]
    SAFE --> EXEC["SQLite<br/>(mode=ro, 5s)"]
    EXEC -- "SQLiteError" --> AGENT
    API -- "append_turn" --> SESS[("Supabase<br/>sessions / turns")]
```

The full component diagram, the `/query` sequence with the fallback decision branch, the safety-pipeline detail, the RAG chunk format, the multi-turn design, the streaming-endpoint protocol, and the module map all live in **[`docs/architecture.md`](docs/architecture.md)**.

<br/>

## Tech stack

<p><b>LLM &amp; vectors</b></p>
<p>
  <img alt="Gemini" src="https://img.shields.io/badge/Gemini_2.5_Flash-1A73E8?style=flat-square&logo=googlegemini&logoColor=white">
  <img alt="Groq" src="https://img.shields.io/badge/Groq_Llama_3.3_70B-F55036?style=flat-square&logo=meta&logoColor=white">
  <img alt="gemini-embedding-001" src="https://img.shields.io/badge/gemini--embedding--001-4285F4?style=flat-square&logo=google&logoColor=white">
  <img alt="pgvector" src="https://img.shields.io/badge/pgvector-0.8-336791?style=flat-square&logo=postgresql&logoColor=white">
</p>

<p><b>Backend</b></p>
<p>
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Pydantic" src="https://img.shields.io/badge/Pydantic_v2-E92063?style=flat-square&logo=pydantic&logoColor=white">
  <img alt="sqlglot" src="https://img.shields.io/badge/sqlglot-AST_safety-222?style=flat-square">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-mode%3Dro-003B57?style=flat-square&logo=sqlite&logoColor=white">
  <img alt="Supabase" src="https://img.shields.io/badge/Supabase-Postgres-3FCF8E?style=flat-square&logo=supabase&logoColor=white">
</p>

<p><b>Frontend</b></p>
<p>
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js_16-000?style=flat-square&logo=nextdotjs&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React_19-61DAFB?style=flat-square&logo=react&logoColor=000">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white">
  <img alt="Tailwind" src="https://img.shields.io/badge/Tailwind_v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white">
  <img alt="React Flow" src="https://img.shields.io/badge/React_Flow-ERD-FF0072?style=flat-square">
  <img alt="Recharts" src="https://img.shields.io/badge/Recharts-charts-22c55e?style=flat-square">
  <img alt="Framer Motion" src="https://img.shields.io/badge/Framer_Motion-0055FF?style=flat-square&logo=framer&logoColor=white">
</p>

<p><b>Infra &amp; CI</b></p>
<p>
  <img alt="HF Spaces" src="https://img.shields.io/badge/Hugging_Face_Spaces-FFD21E?style=flat-square&logo=huggingface&logoColor=000">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-CPU_basic-2496ED?style=flat-square&logo=docker&logoColor=white">
  <img alt="Vercel" src="https://img.shields.io/badge/Vercel-000?style=flat-square&logo=vercel&logoColor=white">
  <img alt="GitHub Actions" src="https://img.shields.io/badge/GitHub_Actions-CI%20%2B%20keepalive-2088FF?style=flat-square&logo=githubactions&logoColor=white">
</p>

Every component is on a permanent free tier. Zero-dollar budget was a hard constraint, not a stretch goal.

<br/>

## Sample databases

Three pre-loaded demo databases ship in the backend image, all opened read-only:

| DB | Tables | Rows | Domain |
|---|---|---|---|
| `northwind` | 13 | ~3K | classic e-commerce — customers, orders, products, suppliers |
| `hr` | 7 | ~1.7K | HR analytics — employees, departments, salaries, performance |
| `ipl` | 8 | ~16.8K | IPL cricket — matches, deliveries, players, teams, venues |

Switch DBs from the sidebar. Each switch resets the conversation — sessions are bound to one schema.

<br/>

## In the UI

<table>
  <tr>
    <td><img src="querymancer-erd-customers-highlight.png" alt="Interactive ERD" width="430"/></td>
    <td><img src="querymancer-schema-tab.png" alt="Schema browser" width="430"/></td>
  </tr>
  <tr>
    <td align="center"><sub><b>Interactive ERD</b> — React Flow + dagre. Click a table to focus its joins; click a column to insert <code>Table.column</code> into the prompt.</sub></td>
    <td align="center"><sub><b>Schema browser</b> — collapsible per-table view with PK / FK highlighting and "REFERENCED BY" sections.</sub></td>
  </tr>
  <tr>
    <td><img src="querymancer-try-tab.png" alt="Curated questions" width="430"/></td>
    <td><img src="querymancer-mobile.png" alt="Mobile layout" width="430"/></td>
  </tr>
  <tr>
    <td align="center"><sub><b>Curated starters</b> — 8 hand-tuned questions per DB to seed exploration.</sub></td>
    <td align="center"><sub><b>Mobile-native</b> — slide-in drawer, full feature parity below the <code>md</code> breakpoint.</sub></td>
  </tr>
</table>

<br/>

## Quickstart

```bash
# 1. clone and enter backend
git clone https://github.com/AryamannSingh7/querymancer.git
cd querymancer/backend

# 2. python deps + env
python -m venv .venv && .venv/Scripts/activate    # Windows
# python -m venv .venv && source .venv/bin/activate   # POSIX
pip install -e ".[dev]"
cp .env.example .env    # then fill GEMINI_API_KEY, SUPABASE_DB_URL, optionally GROQ_API_KEY

# 3. run backend
python -m uvicorn app.main:app --reload
```

```bash
# 4. frontend in another terminal
cd ../frontend
npm ci
BACKEND_URL=http://127.0.0.1:8000 npm run dev
# open http://localhost:3000
```

<details>
<summary><b>Other useful commands</b></summary>

```bash
# index a new SQLite DB into pgvector
cd backend && python -m cli.reindex --db-id <id> --sqlite-path databases/<file>.db

# unit tests (no live LLM / Supabase — conftest stubs both)
cd backend && pytest -q

# eval against a running backend
python eval/run_eval.py --backend http://127.0.0.1:8000 --concurrency 2
# subset filters:
#   --only-db hr            --only-difficulty hard            --limit-per-db 10
```

</details>

<br/>

## Eval

The eval harness (`eval/run_eval.py`) grades 150 cases across 3 DBs and 3 difficulty tiers by row-count assertion. Each report includes:

- pass rate (overall, per-DB, per-difficulty)
- latency `p50` / `p95` / `p99` (client-side, what users feel)
- attempt distribution — how often the self-correction loop kicks in
- failure modes grouped (`UPSTREAM_LLM`, `ASSERTION_FAILED`, `SQL_INVALID`, `TIMEOUT`)
- delta vs previous run

Reports are written incrementally — Ctrl-C leaves a valid partial behind.

> **Baseline status:** numbers are being collected across multiple days. The combined free-tier budget (Gemini 20 RPD + Groq 100K TPD) fits roughly 40-50 successful cases per day at our prompt size — the full 150-case aggregate will land at `eval/reports/` once the HR and IPL slices complete.

<br/>

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo scaffolding, accounts, plan | shipped |
| 1 | Core SQL generation — FastAPI + Gemini 2.5 Flash, structured output | shipped |
| 2 | Safety gate + read-only executor + self-correction loop | shipped |
| 3 | Schema RAG over Supabase pgvector | shipped |
| 4 | Next.js frontend — chat, schema browser, interactive ERD, mobile | shipped |
| 5 | Multi-turn sessions + live "self-correcting…" UX + landing page | shipped |
| 6 | Deployment (HF Spaces + Vercel) + GitHub Actions CI + Groq fallback | shipped |
| 7 | Eval baseline (in progress, paced across multiple days for free-tier quotas), demo video | in progress |

<br/>

## License

MIT.

<br/>

<div align="center">
  <sub>Built by <a href="https://github.com/AryamannSingh7">@AryamannSingh7</a> · <a href="https://querymancer.vercel.app">querymancer.vercel.app</a></sub>
</div>
