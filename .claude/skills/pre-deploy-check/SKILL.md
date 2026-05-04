---
name: pre-deploy-check
description: Run the full preflight gate before pushing to main / deploying. Executes lint, typecheck, unit tests, eval suite, and a smoke /query against the staging backend. Outputs a green/red report — if any item fails, deployment is blocked. Use before every `git push` to main. Examples: "run pre-deploy check", "is this branch ready to ship".
---

Think and act as a senior release engineer. This skill is the deployment gate. If anything is red, the answer is "do not deploy" — no exceptions, no overrides.

## When to invoke

- Before pushing to `main`.
- Before manually triggering the deploy workflow.
- When the user asks "is this ready to ship".

## Workflow

Run these checks. Report each individually with ✅ / ❌. Do not stop on first failure — collect all results so the user sees the full picture.

### 1. Backend lint
```
cd backend && ruff check . && ruff format --check .
```

### 2. Backend type-check
```
cd backend && mypy app/
```

### 3. Backend unit tests
```
cd backend && pytest -q
```

### 4. Frontend lint + typecheck
```
cd frontend && pnpm lint && pnpm typecheck
```

### 5. Frontend build
```
cd frontend && pnpm build
```

### 6. Eval suite (against staging or local backend)
Invoke `eval-runner` agent. Required thresholds:
- Overall success rate ≥ 85%
- p95 latency ≤ 4000 ms
- No new failures vs previous report (if previous exists)

### 7. Smoke `/query`
```
curl -s -X POST <BACKEND_URL>/query \
  -H "Content-Type: application/json" \
  -d '{"question":"how many products are there","database_id":"northwind"}' \
| jq '.rows | length'
```
Expected: integer ≥ 1.

### 8. Health endpoints
```
curl -s <BACKEND_URL>/health   # expect 200
curl -s <FRONTEND_URL>         # expect 200
```

### 9. Secrets check
Grep the staged diff for accidentally-committed secrets (`API_KEY`, `SECRET`, `PASSWORD`, `SUPABASE_KEY` outside `.env.example`). If any non-`.env.example` file mentions these tokens with real-looking values, ❌.

## Output

Print a single status table:
```
✅ Backend lint
✅ Backend types
✅ Backend tests           (24 passed)
✅ Frontend lint + types
✅ Frontend build          (1.8 MB)
✅ Eval suite              (success 92.0%, p95 2.8s, no regressions)
✅ Smoke /query            (returned 77 rows)
✅ Health endpoints
✅ Secrets scan            (clean)

VERDICT: GREEN — safe to deploy
```

If anything is ❌, the verdict is **RED** and the output ends with the literal text:

> Do not push. Fix the failing items above first.

## Quality bar

- Never auto-fix or override a failing check from inside this skill. The skill's job is to report the truth, not to massage it.
- If the eval-runner threshold (85%) is failing, the right next step is invoking the prompt-tuner agent — don't deploy a regression.
- Surface partial results even if the run is interrupted.

## What you do NOT do

- Do not push to remote. The user pushes after the gate is green.
- Do not modify code to make tests pass. That's not what a deploy gate does.
- Do not silently skip steps if a tool isn't installed — fail loudly with the missing-tool name.

## Output to user

Hand back the status table and the explicit verdict (GREEN or RED). If RED, list the exact remediation step for each failure.
