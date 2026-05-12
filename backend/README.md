---
title: Querymancer Backend
emoji: 🪄
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: NL→SQL backend — FastAPI, Gemini, pgvector
---

# Querymancer — backend

FastAPI service that turns a natural-language question into safe, read-only
SQL against a bundled SQLite database. Retrieves relevant schema chunks via
Supabase pgvector, generates SQL with Gemini 2.5 Flash, validates with
`sqlglot`, executes against `mode=ro` SQLite, and self-corrects on failure
(up to 3 attempts).

The frontend lives at <https://github.com/AryamannSingh7/querymancer> (deployed
separately on Vercel) and proxies same-origin to this Space.

## Required Space secrets

| Secret | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio key for `gemini-2.5-flash` and `gemini-embedding-001`. |
| `SUPABASE_DB_URL` | Session-pooler Postgres URL (port 5432, IPv4) for pgvector retrieval and turns persistence. |

Optional overrides: `GEMINI_MODEL` (default `gemini-2.5-flash`),
`EMBED_MODEL` (default `gemini-embedding-001`).

## Endpoints

- `GET  /health` — liveness probe.
- `POST /query` — `{question, database_id, session_id?}` → SQL + rows + chart hint.
- `GET  /databases/{id}/schema` — introspected table/column/FK summary.

## Local run

```bash
docker build -t querymancer-backend .
docker run --rm -p 7860:7860 \
  -e GEMINI_API_KEY=... \
  -e SUPABASE_DB_URL=... \
  querymancer-backend
curl http://localhost:7860/health
```
