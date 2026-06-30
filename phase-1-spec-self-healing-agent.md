# Self-Healing Infrastructure Agent — Phase 1 Specification
## "Local Foundation / Walking Skeleton"

---

## 0. How to use this document

This is a spec-driven build document, written to be handed directly to an agentic coding tool (e.g. Google Antigravity) as the source of truth for what to build. It is intentionally explicit about file paths, schemas, and contracts so the agent doesn't have to guess. Recommended usage:

- Open this file in your project root as context, then ask the agent to produce a task plan from it before writing any code. Review that plan before approving execution.
- Use **Agent-Assisted** mode, not full Autopilot, for this build. Nothing here touches a real cloud account in Phase 1, but `subprocess` execution and file-system writes are exactly the category of action worth eyeballing before it runs.
- Build sections in the order given in §22. Don't let the agent jump ahead to Phase 2 features (retry loops, multiple fixtures, LocalStack, GitHub integration) — see §24 for the explicit "don't build this yet" list.

---

## 1. Where Phase 1 fits in the overall roadmap

| Phase | One-line scope | Status |
|---|---|---|
| **1 — Local Foundation** | One fixture, one fix attempt, full stack working end-to-end, production-grade hygiene from day one | **This document** |
| 2 — Agent Intelligence | Iterative retry loop, full 10-fixture fault library, success-rate scoreboard | Detailed later |
| 3 — Real CI/CD Integration | GitHub Actions detects broken Terraform on a real PR, backend opens a real fix-PR | Detailed later |
| 4 — Real Cloud Target | LocalStack by default; optional real-AWS toggle against Always-Free services (Lambda/S3/DynamoDB) with cost guardrails | Detailed later |
| 5 — Deployment | Vercel + Render + Neon, so there's a live shareable link | Detailed later |
| 6 — Hardening & Polish | Full coverage, security write-up, README, demo video, resume framing | Detailed later |

Come back once Phase 1's Definition of Done (§23) is fully checked off, and the next document will pick up from there.

---

## 2. Phase 1 objective and non-goals

**Objective:** prove the entire pipeline works, end to end, on your local machine, with no shortcuts taken on engineering hygiene — just minimal *functional* scope. One hardcoded broken Terraform file → backend logs it as a failure → a single LLM call proposes a fix → `terraform validate` checks the fix → result stored in Postgres → a Next.js dashboard reflects the outcome live over a WebSocket.

**What "production-grade despite local" means concretely here**, so nothing gets cut as "we'll do it properly later":
- Async SQLAlchemy 2.0 + Alembic migrations from commit #1, not a `Base.metadata.create_all()` shortcut.
- Structured (JSON) logging, not `print()`.
- The LLM never causes a shell command to be built from string concatenation — fixed binary path, argument list, explicit timeout, sandboxed temp directory.
- `terraform validate -json` parsed as structured data, not human-readable text scraped with regex.
- Tests and CI exist before you call this phase "done," not after.
- Config via environment variables through a single typed `Settings` object, never scattered `os.getenv()` calls.

**Explicit non-goals for Phase 1** (full list in §24): no retry loop, no fault library (just one fixture), no LocalStack, no real AWS, no GitHub Actions self-healing trigger, no deployment to cloud hosting, no authentication.

---

## 3. Tech stack (exact)

| Layer | Choice | Notes |
|---|---|---|
| Backend language | Python 3.12+ | |
| Backend framework | FastAPI (`>=0.115`) | async throughout |
| ASGI server | Uvicorn (`uvicorn[standard]>=0.30`) | `--reload` for dev |
| ORM | SQLAlchemy 2.0 (`sqlalchemy[asyncio]>=2.0`) | declarative `Mapped[...]` style, async |
| DB driver | `asyncpg>=0.29` | async Postgres driver |
| Migrations | Alembic (`>=1.13`) | configured for async engine |
| Validation/schemas | Pydantic v2 (`>=2.7`) | also used for LLM structured output |
| Settings | `pydantic-settings>=2.3` | single `Settings` class, reads `.env` |
| LLM SDK | `google-genai>=1.0` | **this is the current GA SDK** — do not install the deprecated `google-generativeai` package |
| Structured logging | `structlog>=24.1` | JSON output |
| Database | PostgreSQL 16, via Docker Compose locally | |
| IaC validation tool | Terraform CLI `>=1.7` (installed on host, not in a container, so `subprocess` can call it directly) | |
| Testing | `pytest`, `pytest-asyncio`, `httpx` (for `AsyncClient`) | |
| Lint/format | `ruff` | replaces black+isort+flake8 |
| Type checking | `mypy` (optional but recommended) | |
| Frontend framework | Next.js 15+ (App Router), TypeScript | |
| Frontend styling | Tailwind CSS | |
| Realtime client | Native browser `WebSocket` API | **do not use `socket.io-client`** — FastAPI's WebSocket support speaks plain WS, not the Socket.IO protocol, and the two are incompatible |
| Package managers | `pip` + `pyproject.toml` (backend), `npm` (frontend) | |

---

## 4. Repository structure (exact)

```
self-healing-agent/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── db.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── deployment.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── deployment.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── deployments.py
│   │   │   └── websocket.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py
│   │   │   ├── terraform_service.py
│   │   │   └── healing_service.py
│   │   └── ws/
│   │       ├── __init__.py
│   │       └── manager.py
│   ├── fixtures/
│   │   └── fault_missing_required_argument/
│   │       ├── main.tf
│   │       └── error_log.txt
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   ├── test_terraform_service.py
│   │   ├── test_llm_service.py
│   │   └── test_deployments_api.py
│   ├── .env.example
│   ├── pyproject.toml
│   ├── docker-compose.yml
│   └── README.md
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── TriggerButton.tsx
│   │   ├── DeploymentList.tsx
│   │   ├── DeploymentDetail.tsx
│   │   └── StatusBadge.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── useDeploymentSocket.ts
│   ├── types/
│   │   └── deployment.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── .env.local.example
│   └── README.md
├── .github/
│   └── workflows/
│       └── backend-ci.yml
└── README.md
```

Every file listed above must exist by the end of Phase 1. Nothing extra (no `Dockerfile` for the backend yet, no `celery_app.py`, no `auth/` folder — those belong to later phases).

---

## 5. Environment & local setup

### 5.1 Backend `.env` (copy from `.env.example`)
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/selfheal
GEMINI_API_KEY=your-key-from-aistudio.google.com
GEMINI_MODEL_NAME=gemini-2.5-flash
TERRAFORM_BINARY_PATH=/usr/local/bin/terraform
TERRAFORM_PLUGIN_CACHE_DIR=/absolute/path/to/.terraform-plugin-cache
LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=http://localhost:3000
```
Note on `GEMINI_MODEL_NAME`: confirm the current free-tier Flash model name in Google AI Studio before first run — model names shift over time. Whatever it is, it lives in exactly **one** place (this env var, read into `Settings`), never hardcoded inside `llm_service.py`.

### 5.2 Frontend `.env.local` (copy from `.env.local.example`)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/deployments
```

### 5.3 `backend/docker-compose.yml`
Defines exactly one service: Postgres 16, exposing `5432`, with a named volume so data survives restarts, healthcheck via `pg_isready`. Database name `selfheal`, user/password `postgres`/`postgres` for local dev only (never used beyond localhost).

### 5.4 Local prerequisites checklist
- Docker + Docker Compose
- Python 3.12+, with a virtualenv
- Node 20+ and npm
- Terraform CLI installed on the host (`terraform -version` should work in a terminal)
- A Gemini API key from Google AI Studio (free tier)

---

## 6. Data model

Two tables, async SQLAlchemy 2.0 declarative style.

### 6.1 `deployments`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | `default=uuid.uuid4` |
| `fault_category` | String(100), not null | Phase 1 always `"missing_required_argument"` |
| `broken_code` | Text, not null | snapshot of the fixture's `main.tf` at trigger time |
| `error_log` | Text, not null | snapshot of the fixture's `error_log.txt` |
| `status` | String(20), not null, default `"FAILED"` | one of `FAILED`, `HEALING`, `HEALED`, `FAILED_TO_HEAL` |
| `created_at` | DateTime(timezone=True), default now | |
| `resolved_at` | DateTime(timezone=True), nullable | set when status becomes `HEALED` or `FAILED_TO_HEAL` |

### 6.2 `healing_attempts`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `deployment_id` | UUID, FK → `deployments.id`, not null | |
| `attempt_number` | Integer, not null, default `1` | always `1` in Phase 1 — the column exists now so Phase 2's retry loop doesn't require a migration |
| `llm_explanation` | Text, not null | model's explanation, or an error message if the LLM call itself failed (see §14) |
| `fixed_code` | Text, not null | model's proposed full corrected file; empty string if the call failed before producing one |
| `validation_success` | Boolean, not null | result of `terraform validate -json` |
| `validation_output` | Text, nullable | raw JSON string from `terraform validate -json` |
| `created_at` | DateTime(timezone=True), default now | |

Use `enum.StrEnum` (Python 3.11+) for the `status` values in application code and Pydantic schemas, even though the column itself is a plain `String` — gives you type safety without an actual Postgres enum migration headache in Phase 1.

### 6.3 Alembic
Configure `alembic/env.py` for the async engine (the standard pattern: wrap migration calls in `asyncio.run()`, run actual DDL synchronously inside that via `connection.run_sync(...)`). Generate the initial revision with `alembic revision --autogenerate -m "create deployments and healing_attempts"`, then `alembic upgrade head`. Do not use `Base.metadata.create_all()` anywhere in application code — migrations are the only way tables get created, including in tests (test fixtures should run migrations against a throwaway test database, or at minimum call `create_all` only inside the test fixture itself, clearly commented as a test-only shortcut).

---

## 7. Backend architecture — module responsibilities

- **`core/config.py`** — one `Settings(BaseSettings)` class reading every env var from §5.1. Imported everywhere as `from app.core.config import settings`.
- **`core/db.py`** — creates the async engine and `AsyncSessionLocal` factory; exposes a `get_db` FastAPI dependency (`async def get_db() -> AsyncIterator[AsyncSession]`) that yields a session and closes it after the request.
- **`core/logging.py`** — configures `structlog` once at startup to emit JSON to stdout, including a request-scoped or deployment-scoped `deployment_id` field where relevant.
- **`models/deployment.py`** — the two ORM classes from §6.
- **`schemas/deployment.py`** — Pydantic models: `DeploymentSummary`, `DeploymentDetail`, `HealingAttemptOut`. These are the API response shapes — never return ORM objects directly from a route.
- **`services/llm_service.py`** — owns all Gemini SDK calls (§11). Exposes one function: `async def generate_fix(broken_code: str, error_log: str) -> FixResult`.
- **`services/terraform_service.py`** — owns the sandbox + subprocess logic (§12). Exposes one function: `async def validate_terraform(code: str) -> ValidationResult`.
- **`services/healing_service.py`** — the orchestrator (§13). Exposes `async def run_healing_cycle(deployment_id: UUID, db: AsyncSession) -> None`, called as a background task.
- **`api/health.py`**, **`api/deployments.py`**, **`api/websocket.py`** — routers, one per concern, all included from `main.py` via `app.include_router(...)`.
- **`ws/manager.py`** — a `ConnectionManager` class holding the set of active WebSocket connections and a `broadcast(message: dict)` method.
- **`main.py`** — creates the FastAPI app, configures `CORSMiddleware` using `settings.CORS_ALLOWED_ORIGINS`, calls the logging setup, includes all routers. No business logic lives here.

---

## 8. API contract — every endpoint, in full

### 8.1 `GET /api/health`
- No auth, no params.
- Response `200`: `{"status": "ok"}`

### 8.2 `POST /api/deployments/trigger`
- No request body required (send `{}` or nothing).
- Behavior: loads the Phase 1 fixture from disk (`fixtures/fault_missing_required_argument/`), creates a `deployments` row with `status="FAILED"`, commits, schedules `run_healing_cycle` as a background task (FastAPI `BackgroundTasks`, or `asyncio.create_task` — either is acceptable in Phase 1; document your choice in the backend README), broadcasts the initial state over the WebSocket (see §9), and returns immediately.
- Response `201`:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "fault_category": "missing_required_argument",
  "status": "FAILED",
  "created_at": "2026-06-19T10:00:00Z",
  "resolved_at": null
}
```
- This call must return in well under a second — it must never block on the LLM call or the Terraform subprocess.

### 8.3 `GET /api/deployments`
- No params (pagination is a Phase 2+ concern — Phase 1 will only ever have a handful of rows).
- Response `200`: array of the same shape as §8.2's response, ordered by `created_at` descending.

### 8.4 `GET /api/deployments/{deployment_id}`
- Path param: `deployment_id` (UUID).
- Response `200`:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "fault_category": "missing_required_argument",
  "status": "HEALED",
  "broken_code": "...",
  "error_log": "...",
  "created_at": "2026-06-19T10:00:00Z",
  "resolved_at": "2026-06-19T10:00:04Z",
  "attempts": [
    {
      "id": "...",
      "attempt_number": 1,
      "llm_explanation": "The aws_lambda_function resource was missing the required `runtime` argument...",
      "fixed_code": "...",
      "validation_success": true,
      "validation_output": "{\"valid\":true,\"diagnostics\":[]}",
      "created_at": "2026-06-19T10:00:04Z"
    }
  ]
}
```
- Response `404` if the ID doesn't exist: `{"detail": "Deployment not found"}`

---

## 9. WebSocket protocol

- Endpoint: `WS /ws/deployments`
- On connect: server does nothing proactively. The client is responsible for calling `GET /api/deployments` right after connecting to populate history; the socket only carries *new* events from that point forward.
- The server broadcasts to **every** connected client (not just the one who triggered the run) on each status transition: creation (`FAILED`), `HEALING`, and the terminal state (`HEALED` or `FAILED_TO_HEAL`). This keeps multiple open browser tabs in sync.
- Message shape, identical on every broadcast:
```json
{
  "type": "deployment_update",
  "data": { /* same shape as §8.4's response body */ }
}
```
- No client-to-server messages are expected or handled in Phase 1 — it's a one-way push channel. If the client sends anything, the server should simply ignore it (don't error/disconnect).
- Handle disconnects gracefully: wrap the receive loop in a `try/except WebSocketDisconnect` and remove the connection from the manager's set in a `finally` block.

---

## 10. The Phase 1 fault fixture

### 10.1 `backend/fixtures/fault_missing_required_argument/main.tf`
```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_lambda_function" "healer_demo" {
  function_name = "self-healing-demo-fn"
  role          = "arn:aws:iam::123456789012:role/lambda-demo-role"
  filename      = "function.zip"
  handler       = "index.handler"
  # NOTE: "runtime" is a required argument for aws_lambda_function and is
  # intentionally omitted here — this is the bug Phase 1 exists to catch and fix.
}
```

### 10.2 `backend/fixtures/fault_missing_required_argument/error_log.txt`
```
[2026-06-19T10:00:00Z] INFO  Starting deployment pipeline run #1
[2026-06-19T10:00:01Z] INFO  Running: terraform init
[2026-06-19T10:00:03Z] INFO  Terraform has been successfully initialized!
[2026-06-19T10:00:03Z] INFO  Running: terraform validate
[2026-06-19T10:00:04Z] ERROR Error: Missing required argument
[2026-06-19T10:00:04Z] ERROR   on main.tf line 13, in resource "aws_lambda_function" "healer_demo":
[2026-06-19T10:00:04Z] ERROR   13: resource "aws_lambda_function" "healer_demo" {
[2026-06-19T10:00:04Z] ERROR The argument "runtime" is required, but no definition was found.
[2026-06-19T10:00:04Z] FATAL  Deployment pipeline failed at validation stage. Halting rollout.
```

These two files are loaded as plain text and copied verbatim into the `deployments` row at trigger time — they are never mutated on disk.

---

## 11. LLM integration (Gemini via `google-genai`)

### 11.1 Client setup
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.GEMINI_API_KEY)
```

### 11.2 Structured output schema
```python
from pydantic import BaseModel

class FixResult(BaseModel):
    explanation: str
    fixed_code: str
```

### 11.3 The call
```python
PROMPT_TEMPLATE = """You are an expert Site Reliability Engineer specializing in Terraform/HCL.
You will be given a broken Terraform configuration file and the error log from a failed
deployment pipeline. Identify the bug, explain it in 1-3 sentences, and return the FULL
corrected file. Preserve every existing block (provider, required_providers, all resource
arguments that are not the bug) — change only what is needed to fix the reported error.

BROKEN FILE:
{broken_code}

ERROR LOG:
{error_log}
"""

async def generate_fix(broken_code: str, error_log: str) -> FixResult:
    response = await client.aio.models.generate_content(
        model=settings.GEMINI_MODEL_NAME,
        contents=PROMPT_TEMPLATE.format(broken_code=broken_code, error_log=error_log),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FixResult,
        ),
    )
    return FixResult.model_validate_json(response.text)
```
Use the **async** client (`client.aio.models.generate_content`) since the rest of the stack is async — don't block the event loop with the sync client.

### 11.4 Failure handling
Wrap the call site (in `healing_service.py`, not inside `llm_service.py` itself) in a try/except. Network errors, quota errors, and schema-validation errors on the response are all realistic in Phase 1 (you're on a free tier) — see §14 for what to do when this happens.

---

## 12. Terraform validation service

### 12.1 Why `-json` matters
`terraform validate -json` returns machine-readable structured diagnostics instead of human-formatted text. Parse this JSON directly — never regex-match plain validate output. The shape includes a top-level `"valid": true|false` boolean and a `"diagnostics"` array; store the raw JSON string in `validation_output` and use the `valid` field to set `validation_success`.

### 12.2 Plugin cache (don't skip this)
Every validation run uses a **fresh** temp directory for isolation, which means `terraform init` has to run before `validate` every single time (Terraform requires init before validate). Without a shared plugin cache, that means re-downloading the AWS provider plugin from the registry on every single run — slow and needlessly network-dependent. Fix: set `TF_PLUGIN_CACHE_DIR` to a **persistent** directory outside the ephemeral sandbox, created once at app startup (`mkdir -p`). Every sandboxed `init` reuses the cached provider binary instead of re-fetching it.

### 12.3 Exact flow
```python
import subprocess, tempfile, os, json
from pathlib import Path

async def validate_terraform(code: str) -> ValidationResult:
    with tempfile.TemporaryDirectory(prefix="heal-") as sandbox:
        (Path(sandbox) / "main.tf").write_text(code)

        env = {
            "PATH": os.environ["PATH"],
            "TF_PLUGIN_CACHE_DIR": settings.TERRAFORM_PLUGIN_CACHE_DIR,
            "TF_IN_AUTOMATION": "1",
        }

        init = subprocess.run(
            [settings.TERRAFORM_BINARY_PATH, "init", "-backend=false", "-input=false", "-no-color"],
            cwd=sandbox, env=env, capture_output=True, text=True, timeout=60,
        )
        if init.returncode != 0:
            return ValidationResult(valid=False, raw_output=init.stderr)

        validate = subprocess.run(
            [settings.TERRAFORM_BINARY_PATH, "validate", "-json", "-no-color"],
            cwd=sandbox, env=env, capture_output=True, text=True, timeout=30,
        )
        parsed = json.loads(validate.stdout)
        return ValidationResult(valid=parsed["valid"], raw_output=validate.stdout)
```

### 12.4 Non-negotiable security rules
- Argument lists only — **never** `shell=True`, **never** string-concatenated commands.
- A fixed, configured binary path (`settings.TERRAFORM_BINARY_PATH`), not a bare `"terraform"` resolved from whatever `PATH` happens to contain.
- An explicit, minimal `env` dict passed to `subprocess.run` — don't blindly inherit the full parent environment.
- An explicit `timeout` on every call — a hung subprocess must not hang the request.
- The sandbox directory is always a fresh `tempfile.TemporaryDirectory()`, auto-deleted on exit — the LLM's output is never written into any path inside your actual repository.
- `validate` performs no cloud API calls and needs no credentials — this is exactly why Phase 1 can run with zero cloud accounts.

---

## 13. Orchestration flow (`healing_service.run_healing_cycle`)

Step by step, this is the entire Phase 1 "brain":

1. Fetch the `deployments` row by ID.
2. Set `status = "HEALING"`, commit, broadcast over WebSocket.
3. Call `llm_service.generate_fix(deployment.broken_code, deployment.error_log)`.
   - On exception: create a `healing_attempts` row with `llm_explanation="LLM call failed: {error}"`, `fixed_code=""`, `validation_success=False`, `validation_output=None`; set deployment `status="FAILED_TO_HEAL"`, `resolved_at=now()`; commit; broadcast; log the exception; **return** (skip steps 4-6).
4. Call `terraform_service.validate_terraform(fix_result.fixed_code)`.
5. Create a `healing_attempts` row: `attempt_number=1`, `llm_explanation=fix_result.explanation`, `fixed_code=fix_result.fixed_code`, `validation_success=validation_result.valid`, `validation_output=validation_result.raw_output`.
6. Set deployment `status = "HEALED"` if `validation_result.valid` else `"FAILED_TO_HEAL"`; set `resolved_at = now()`; commit; broadcast the final state.

This function takes a `db: AsyncSession` parameter rather than opening its own — when called as a background task, open a **new** session scoped to the task (don't reuse a request-scoped session after the request has returned).

---

## 14. Error handling rules (summary)

| Failure point | Resulting deployment status | What gets recorded |
|---|---|---|
| LLM call throws (network, quota, malformed response) | `FAILED_TO_HEAL` | attempt row with the error message in `llm_explanation`, empty `fixed_code` |
| LLM returns a fix, but `terraform validate` says invalid | `FAILED_TO_HEAL` | attempt row with the real explanation, the (still-broken) fixed code, and the validator's diagnostics — **this is an expected, acceptable outcome in Phase 1**, not a bug to chase. It's exactly the gap Phase 2's retry loop exists to close. |
| LLM returns a fix that validates successfully | `HEALED` | full attempt row, `validation_success=True` |
| `terraform init`/`validate` itself throws (binary missing, timeout) | `FAILED_TO_HEAL` | attempt row with the subprocess error captured in `validation_output` |

Every path above must still produce exactly one `healing_attempts` row and one final WebSocket broadcast — there is no silent failure state.

---

## 15. Logging & observability

Configure `structlog` once in `core/logging.py`, JSON renderer, to stdout. Emit at minimum these events, each with `deployment_id` bound where applicable:
- `deployment.created` (fault_category)
- `healing.started`
- `llm.fix_generated` (or `llm.call_failed` with the error)
- `terraform.validation_result` (valid: bool)
- `deployment.resolved` (final status)

This audit trail, combined with the `healing_attempts` table, **is** your observability story for Phase 1 — no external logging service needed yet.

---

## 16. Security notes specific to Phase 1

- LLM output is data, never code that gets executed directly — it is only ever written to a file and read back by `terraform validate`, never `eval`'d, never passed to a shell.
- `.env` is git-ignored; `.env.example` documents every key with placeholder values, never real ones.
- CORS is restricted to `settings.CORS_ALLOWED_ORIGINS` (your local frontend origin only) — not `allow_origins=["*"]`.
- No authentication is implemented in Phase 1 (explicitly out of scope, §24) — this is acceptable only because the whole thing runs on localhost. Note this limitation explicitly in the backend README so it's never mistaken for an oversight later.

---

## 17. Testing requirements

| File | What it must assert |
|---|---|
| `tests/test_health.py` | `GET /api/health` → `200`, `{"status": "ok"}` |
| `tests/test_terraform_service.py` | (a) validating the known-broken fixture's `main.tf` returns `valid=False`; (b) validating a trivial known-good Terraform snippet (a single `aws_s3_bucket` with all required args) returns `valid=True`. Runs against the **real** Terraform binary — no mocking here. |
| `tests/test_llm_service.py` | Mocks the `google-genai` client entirely (no real network call, no real API key needed in CI). Verifies the prompt includes both `broken_code` and `error_log`, and that a fabricated structured response is correctly parsed into a `FixResult`. |
| `tests/test_deployments_api.py` | Using `httpx.AsyncClient` against the FastAPI app with a test database: `POST /api/deployments/trigger` → `201` with `status="FAILED"`; after awaiting the background task to complete (mock `llm_service.generate_fix` to return a known-good fix so this test doesn't depend on a live API key or quota, but let the **real** `terraform_service` run), `GET /api/deployments/{id}` → `status="HEALED"` with one attempt recorded. |

`conftest.py` should provide: an async test database fixture (a separate Postgres database, e.g. `selfheal_test`, with migrations applied — not SQLite, since you want real Postgres-specific behavior verified), and an `AsyncClient` fixture wired to the app with that test database overridden via FastAPI's dependency-override mechanism.

---

## 18. CI workflow — `.github/workflows/backend-ci.yml`

```yaml
name: Backend CI

on:
  push:
    paths: ["backend/**"]
  pull_request:
    paths: ["backend/**"]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: selfheal_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.0"
      - name: Install dependencies
        working-directory: backend
        run: pip install -e ".[dev]"
      - name: Lint
        working-directory: backend
        run: ruff check .
      - name: Run migrations against test DB
        working-directory: backend
        run: alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/selfheal_test
      - name: Run tests
        working-directory: backend
        run: pytest -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/selfheal_test
          GEMINI_API_KEY: dummy-not-used-in-ci
          TERRAFORM_BINARY_PATH: terraform
          TERRAFORM_PLUGIN_CACHE_DIR: /tmp/tf-plugin-cache
```
This runs on a public repo, so it's free with no minute cap (per GitHub's current free-tier terms for public repositories). Keep the repo public for this reason.

---

## 19. Frontend specification

### 19.1 Pages
- `app/page.tsx` — the single dashboard page. On mount: `fetch` `GET /api/deployments` to populate history, then open the WebSocket and subscribe to live updates for the rest of the session.

### 19.2 Components
- **`TriggerButton.tsx`** — a button labeled "Run Demo". `onClick` → `POST /api/deployments/trigger`. Disable it while a deployment is actively `HEALING` to avoid pile-ups (Phase 1 only ever runs one at a time by convention, not by backend enforcement).
- **`DeploymentList.tsx`** — renders the history array (newest first): id (shortened), fault category, status badge, created_at. Clicking a row selects it for the detail view.
- **`DeploymentDetail.tsx`** — for the selected deployment, render four labeled panels in monospace `<pre>` blocks: Broken Code, Error Log, LLM Explanation (+ Fixed Code), Validation Output. Show a clear visual state for each of the four statuses (`FAILED`, `HEALING` — show a spinner, `HEALED` — success styling, `FAILED_TO_HEAL` — failure styling).
- **`StatusBadge.tsx`** — small reusable colored badge component, one variant per status string.

### 19.3 Data layer
- **`lib/api.ts`** — thin wrapper functions: `triggerDeployment()`, `listDeployments()`, `getDeployment(id)`, each typed against `types/deployment.ts` interfaces and hitting `process.env.NEXT_PUBLIC_API_BASE_URL`.
- **`lib/useDeploymentSocket.ts`** — a custom hook that opens a native `WebSocket` to `process.env.NEXT_PUBLIC_WS_URL` on mount, parses incoming `{"type":"deployment_update","data":{...}}` messages, and exposes the latest update to the component tree (e.g. via a callback prop or a small context — either is fine, keep it simple, no external state library needed for this scope). Must clean up (close the socket) on unmount.
- **`types/deployment.ts`** — TypeScript interfaces mirroring §8.4's response shape exactly: `Deployment`, `HealingAttempt`.

### 19.4 What the UI must visibly demonstrate
A reviewer should be able to: load the page, click "Run Demo," watch the new entry appear and transition live from FAILED → HEALING → a terminal state with no manual refresh, click it, and read the full story (what was broken, what the model said, what it changed, whether it actually validated).

---

## 20. Linting, formatting, type-checking

`backend/pyproject.toml` must include:
```toml
[project]
name = "self-healing-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlalchemy[asyncio]>=2.0",
  "asyncpg>=0.29",
  "alembic>=1.13",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "google-genai>=1.0",
  "structlog>=24.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27", "ruff>=0.5", "mypy>=1.10"]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
```
Run `ruff check .` and `ruff format .` before every commit; CI fails the build if `ruff check .` reports anything.

---

## 21. README requirements

`backend/README.md` and `frontend/README.md` must each document, at minimum: prerequisites, exact setup commands (`docker compose up -d`, `alembic upgrade head`, `uvicorn app.main:app --reload` / `npm install && npm run dev`), required env vars with where to obtain them, and how to run the test suite. The root `README.md` links to both and states plainly that this is Phase 1 of a larger build (link forward to where Phase 2+ will live once written).

---

## 22. Build order within Phase 1

Work through these in order — each one should be runnable/testable before moving to the next:

1. Scaffold the repo structure from §4. `docker compose up -d` brings up Postgres; confirm with `psql` or any client that you can connect.
2. Write `core/config.py`, `core/db.py`, the two ORM models, and the initial Alembic migration. Confirm `alembic upgrade head` creates both tables correctly.
3. Build the FastAPI skeleton: `main.py` + `api/health.py` only. Confirm `GET /api/health` works.
4. Add the fixture files (§10) and `schemas/deployment.py`.
5. Build `services/terraform_service.py` in isolation, with its test, before touching the LLM — confirm `terraform validate` against both the broken fixture and a known-good snippet behaves as expected, including the plugin cache actually being reused on the second run.
6. Build `services/llm_service.py` with its mocked test. Manually smoke-test it once against the real API with a throwaway script to confirm your prompt/schema actually works against the real model before wiring it into the orchestrator.
7. Build `services/healing_service.py`, then `api/deployments.py` (both REST endpoints), wiring everything together. Confirm the full cycle end-to-end via `curl` or the FastAPI `/docs` page.
8. Build `ws/manager.py` and `api/websocket.py`. Confirm with a simple WebSocket test client (or browser dev console) that triggering a deployment produces the expected broadcast sequence.
9. Write the remaining backend tests (§17) and the CI workflow (§18). Get CI green.
10. Build the frontend: layout/page skeleton first, then `TriggerButton` + REST calls, then `DeploymentList`, then the WebSocket hook, then `DeploymentDetail`.
11. Write both READMEs.
12. Walk through the Definition of Done (§23) line by line.

---

## 23. Definition of Done — Phase 1 acceptance checklist

- [ ] `docker compose up -d` brings up Postgres locally with no manual intervention
- [ ] `alembic upgrade head` creates `deployments` and `healing_attempts` with the exact columns in §6
- [ ] `uvicorn app.main:app --reload` starts cleanly; `GET /api/health` returns `200`
- [ ] `POST /api/deployments/trigger` returns `201` in well under a second, with `status="FAILED"`
- [ ] Within a few seconds, the deployment visibly transitions `FAILED → HEALING → HEALED` or `FAILED_TO_HEAL`, observable both via `GET /api/deployments/{id}` and via the WebSocket — no polling required on the client
- [ ] Re-running the trigger multiple times produces a sensible mix of `HEALED`/`FAILED_TO_HEAL` outcomes (the LLM won't be 100% deterministic — this is expected and fine in Phase 1, not a bug)
- [ ] The dashboard at `localhost:3000` shows the "Run Demo" button, a live-updating history list, and a detail view with all four data panels from §19.2
- [ ] `pytest` passes locally and in GitHub Actions
- [ ] `ruff check .` passes with zero errors
- [ ] No secrets are committed anywhere in git history; `.env` is in `.gitignore`; `.env.example` is accurate and complete
- [ ] Both `README.md` files are accurate enough that a stranger could clone the repo and get it running from the instructions alone

When every box above is checked, Phase 1 is done. Come back and we'll write Phase 2 (the retry loop, the full fault library, and the scoreboard).

---

## 24. Explicitly out of scope for Phase 1 — do not build these yet

- A retry/iterative loop of any kind (one fix attempt only)
- More than one fault fixture
- LocalStack or any real AWS interaction
- GitHub Actions triggering the healing flow on a real PR (only the backend's own test/lint CI from §18 exists in Phase 1)
- Deployment to Vercel/Render/Neon or any hosting provider
- Authentication or authorization of any kind
- Celery, Redis, or any external task queue (FastAPI's own async background task mechanism is sufficient at this scale)
- Rate limiting, multi-tenancy, or anything resembling a "real users" concern
- Syntax highlighting libraries, design polish, or any frontend dependency beyond what's listed in §3 — plain, functional, monospace-and-Tailwind is enough for Phase 1
