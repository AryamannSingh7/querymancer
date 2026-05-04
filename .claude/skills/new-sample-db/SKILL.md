---
name: new-sample-db
description: End-to-end addition of a new sample database to Querymancer — generates schema + seed, indexes the schema into pgvector, generates demo questions, wires the UI selector, and adds eval cases. One invocation, four sub-agents orchestrated, four files updated. Use when adding a 4th demo DB or replacing an existing one. Examples: "add a logistics database to the demo", "replace the IPL db with an IMDb-style movies db".
---

Think and act as a senior data engineer orchestrating a multi-stage pipeline. This skill chains the sample-db-generator → schema-indexer → demo-question-generator agents and then wires the result into the eval suite, all in the right order.

## When to invoke

- The user wants a new sample database added to the demo experience.
- An existing sample DB is being replaced (slug must be different — never silently overwrite).

## Inputs to confirm with user

- Target domain (e.g. "logistics", "publishing", "movies")
- Slug (default: derived from domain, e.g. "logistics")
- Optional theme constraints (e.g. "Indian context, INR currency")

## Workflow

Run these stages **sequentially** — each depends on the previous.

### Stage 1: Schema + seed
Invoke `sample-db-generator` agent with the domain. It will:
- Design the schema (5-10 tables, FKs, mixed types)
- Write `scripts/generate_<slug>_db.py`
- Run it to produce `backend/databases/<slug>.db`
- Wire the slug into `backend/app/models.py` enum and `frontend/lib/databases.ts`

Verify: `.db` file exists, row counts > 0 in expected tables.

### Stage 2: Embed the schema
Invoke `schema-indexer` agent with `database_id=<slug>`. It will:
- Introspect the new `.db`
- Build per-table chunks
- Embed via Gemini
- Upsert into Supabase `schema_embeddings`

Verify: Supabase has new rows for the slug.

### Stage 3: Demo questions
Invoke `demo-question-generator` agent with the slug. It will:
- Inspect schema and sample data
- Write 8-12 questions across difficulty bands
- Validate each `expected_sql` actually runs
- Save to `frontend/lib/demo_questions/<slug>.json`

### Stage 4: Eval cases
Hand-write OR have the demo-question-generator extend its output to also seed `eval/cases.yaml` with 10-20 questions for the new DB. Each case needs `expected_min_rows` / `expected_columns_subset` assertions.

### Stage 5: Smoke test
Run `python -m backend.cli ask --db <slug> --question "<one of the demo questions>"` end-to-end. Assert: SQL is generated, executes, returns ≥1 row.

## Quality bar

- Stages MUST run in order. Do not parallelise; later stages depend on earlier ones.
- If any stage fails, halt and report — do not proceed to later stages with broken inputs.
- The new slug must not collide with an existing one. Check both backend enum and frontend list.
- Final smoke test must pass before you declare the skill done.

## What you do NOT do

- Do not modify the eval-runner's report format.
- Do not change the prompt builder. If demo questions for a new DB are failing systematically, that's a prompt-tuner concern.
- Do not push to the deployed backend until the local smoke test passes.

## Output to user

Hand back: slug, the .db file path, Supabase row count for the slug, demo-question file path, eval cases added, smoke-test result. One paragraph total.
