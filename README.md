# Querymancer

**Conversational analytics over multi-schema databases.** Ask a database in plain English, get SQL, results, and visualisations back — with retrieval-augmented schema context, an agentic self-correction loop, and a production-grade safety pipeline so generated SQL never touches anything it shouldn't.

> Status: 🚧 in active development. Phase 0 (scaffolding).

## What it does

You type *"which 5 products generated the most revenue last quarter?"* against a connected database. Querymancer:

1. **Retrieves** the relevant table and column descriptions for your question via vector search over schema embeddings (RAG).
2. **Generates** SQL with an LLM, returning a structured response that includes the query, an explanation, and a suggested chart type.
3. **Validates** the SQL through a multi-layer safety gate (AST parse → keyword denylist → single-statement check → auto-`LIMIT` injection).
4. **Executes** it against a read-only database connection with a 5-second timeout.
5. **Self-corrects** if execution fails — the verbatim DB error is fed back into the next prompt attempt, up to 3 retries.
6. **Renders** results as a table plus an auto-selected chart (bar, line, pie, metric) — whichever matches the result shape.

Multi-turn refinement is built in: ask a follow-up like *"now break it down by category"* and the system understands the prior turn.

## Architecture at a glance

```
[Next.js UI · Vercel]
        │
        ▼
[FastAPI · Hugging Face Spaces]
   ├─ Embed question → Gemini embedding-001
   ├─ Vector search → Supabase pgvector (top-K schema chunks)
   ├─ Generate SQL → Gemini 2.5 Flash (structured output)
   ├─ Safety gate → sqlglot AST + denylist + LIMIT
   ├─ Execute → SQLite (mode=ro, 5s timeout)
   └─ Self-correct on error (max 3 attempts)
        │
        ▼
[Table + Chart · Tremor]
```

A more detailed diagram and end-to-end sequence flow will live in `docs/architecture.md` once Phase 6 ships.

## Tech stack

| Layer | Choice |
|---|---|
| LLM | Google Gemini 2.5 Flash (free tier, structured output) |
| Embeddings | Google `gemini-embedding-001` |
| Vector store + app DB | Supabase Postgres with pgvector |
| Sample databases | SQLite, bundled in the backend image, opened read-only |
| Backend | FastAPI (Python 3.11) |
| SQL safety | `sqlglot` AST validation + keyword denylist |
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui |
| Charts | Tremor |
| Backend hosting | Hugging Face Spaces (Docker, CPU Basic) |
| Frontend hosting | Vercel Hobby |
| Observability | Sentry (free tier) |

Every component is on a permanent free tier — no credit card required anywhere.

## Sample databases

Three pre-loaded demo databases ship with the system:

1. **Northwind** — classic e-commerce schema (customers, orders, products, suppliers)
2. **HR analytics** — employees, departments, salaries, performance reviews
3. **IPL cricket stats** — matches, deliveries, players, teams, venues

You can ask questions across any of them and switch on the fly.

## Roadmap

- [x] Phase 0 — repo scaffolding, accounts, plan
- [ ] Phase 1 — core SQL generation (FastAPI + Gemini, hardcoded schema)
- [ ] Phase 2 — safety gate + executor + self-correction loop
- [ ] Phase 3 — schema RAG over pgvector
- [ ] Phase 4 — Next.js MVP frontend
- [ ] Phase 5 — multi-turn conversation + polish
- [ ] Phase 6 — deployment (HF Spaces + Vercel)
- [ ] Phase 7 — eval suite + docs + demo video

A live demo URL will be linked here once Phase 6 ships.

## Local setup

> Coming in Phase 1. The scaffold isn't wired yet.

## License

MIT — see [LICENSE](LICENSE) (to be added).
