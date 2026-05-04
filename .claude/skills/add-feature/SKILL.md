---
name: add-feature
description: Scaffold the standard pattern for a new backend+frontend feature in Querymancer. Use when adding a feature that touches both an API endpoint and a UI component. Examples: "add a /save-query endpoint and a Saved tab", "scaffold a feature for exporting results to CSV". Skips work if the feature is purely backend or purely frontend — those are simpler one-shot edits.
---

Think and act as a senior full-stack engineer. This skill scaffolds the typical pattern for a Querymancer feature so naming, structure, and tests stay consistent across the codebase.

## When to invoke

- Feature touches BOTH the backend (route + core logic) AND the frontend (component + state).
- Feature is non-trivial (>1 file each side).

## When NOT to invoke

- Pure backend internal helper — just edit the relevant `backend/app/core/` module.
- Pure CSS / styling tweak — edit the component directly.
- One-line bug fix — fix it, don't scaffold.

## Workflow

Ask the user (if not already in the prompt) for:
- **Feature name** in kebab-case (e.g. `save-query`)
- **One-line purpose** (e.g. "let users bookmark a generated SQL for later")
- **API contract** — request shape, response shape, HTTP method, auth required?

Then scaffold in this order:

### 1. Backend
- Create `backend/app/routers/<feature>.py` with FastAPI router (mirror existing routers' style)
- Add Pydantic request/response models in `backend/app/models.py` under a clearly-named section (do not edit unrelated models)
- Wire the router into `backend/app/main.py` (`app.include_router(...)`)
- Add unit tests in `backend/tests/test_<feature>.py` covering: happy path, validation error, edge case
- If the feature touches Supabase, add the migration to `scripts/migrations/<ts>_<feature>.sql`

### 2. Frontend
- Create `frontend/components/<Feature>.tsx` (PascalCase) — keep it as a controlled component
- Add TS types to `frontend/lib/types.ts` (or generate from backend OpenAPI via `openapi-typescript`)
- Add the API call in `frontend/lib/api.ts` — typed, with error handling
- Wire the component into the relevant page (`app/chat/page.tsx` or wherever)
- Apply existing Tailwind / shadcn patterns — do not introduce new style conventions

### 3. Docs / consistency
- Add a one-line entry to README's "Features" list (if there is one)
- Mention the new endpoint in the OpenAPI summary docstring
- If the feature affects the architecture, schedule the architecture-doc-writer agent to refresh docs

## Quality bar

- No copy-pasted code across feature files. If you find yourself duplicating > 5 lines, extract a helper.
- Tests must run and pass before you call this skill done.
- The backend route MUST validate input via Pydantic. Never trust the frontend to enforce constraints.
- The frontend MUST handle: loading state, error state, empty state. No silent failures.

## Output to user

Hand back the list of files created/modified, the URL of the new endpoint (e.g. `POST /api/<feature>`), and the literal command to run the new tests (e.g. `pytest backend/tests/test_<feature>.py`).
