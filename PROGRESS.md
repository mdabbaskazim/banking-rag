# Banking RAG - Implementation Progress

## Status Overview

| Phase | Description | Status | Completed Date |
|---|---|---|---|
| **0** | **Foundations, Quality Tools, Core Configuration & API Skeleton** | **COMPLETED** | 2026-10-29 |
| 1 | API skeleton, database models, first migrations | Not Started | Pending Phase 0 approval |
| 2 | Ingestion without LLM (Docling parse, table-safe chunking, dedupe) | Not Started | - |
| 3 | BGE-M3 embeddings, Qdrant collection, hybrid retrieval | Not Started | - |
| 4 | Query graph happy path (gate, generate, render, rate limiter, fake LLM) | Not Started | - |
| 5 | Verification (quote, numeric, entailment, retry routing) | Not Started | - |
| 6 | Durability and HITL (checkpointer, interrupt, review API, Gradio) | Not Started | - |
| 7 | Reliability (RetryPolicy, circuit breaker, Procrastinate worker) | Not Started | - |
| 8 | Evals and CI gates | Not Started | - |
| 9 | Observability (Langfuse Cloud, audit views) | Not Started | - |
| 10 | Docker (multi-stage Dockerfile, docker-compose.yml, SCALING.md) | Not Started | - |

---

## Phase 0: Foundations & Quality Tools

### Completed Work

- [x] **Project Packaging & Dependencies**:
  - Configured `pyproject.toml` with runtime, development, and eval groups according to ARCHITECTURE.md Section 3.
  - Generated and verified `uv.lock` with Python 3.12 (`76 packages resolved`).
  - Configured build system using `hatchling` for editable wheel installation of `src/bankrag`.
- [x] **Core Configuration (`src/bankrag/core/config.py`)**:
  - Implemented `Settings` class with full validation for all ARCHITECTURE.md Section 11 parameters.
  - Implemented cloud deployment validation (`validate_cloud_requirements`) and parsed `risky_topics_list`.
  - Configured `.env` file loading with environment variable precedence.
- [x] **Structured Logging (`src/bankrag/core/logging.py`)**:
  - Implemented `structlog` configuration outputting JSON to stdout.
  - Added recursive secret redaction for API keys, passwords, tokens, and credentials.
  - Enforced Engineering Rule 10: User questions are automatically masked to SHA-256 hash (12 chars) and character length at INFO and below.
- [x] **Core Errors & IDs (`src/bankrag/core/errors.py`, `src/bankrag/core/ids.py`)**:
  - Built typed exception hierarchy: `BankRagError`, `ConfigurationError`, `ProviderError`, `RateLimitExceededError`, `CircuitBreakerOpenError`, `DatabaseError`, `VectorStoreError`, `VerificationError`, `ServiceUnavailableError`.
  - Implemented deterministic chunk ID generation using UUID5 under a fixed namespace: `uuid5(BANKRAG_CHUNK_NAMESPACE, f"{doc_id}:{version}:{chunk_index}")`.
  - Implemented UUID4 thread ID and SHA-256 content hashing helpers.
- [x] **Provider Interfaces & Fakes (`src/bankrag/providers/`)**:
  - Defined provider abstractions: `LLMProvider`, `VectorStoreProvider`, `RateLimiterProvider`, `EmbeddingProvider`, `EntailmentProvider`.
  - Implemented zero-credential in-memory test fakes: `FakeLLMProvider`, `FakeVectorStoreProvider`, `FakeRateLimiterProvider`.
- [x] **FastAPI Application & Endpoints (`src/bankrag/api/`)**:
  - `GET /health`: Liveness probe performing zero I/O and no external dependencies.
  - `GET /ready`: On-demand readiness probe checking Neon Postgres and Qdrant connectivity with accurate failure reporting.
  - Structured lifespan logger reporting startup and graceful shutdown.
- [x] **Alembic Baseline Migration (`alembic.ini`, `migrations/`)**:
  - Configured `alembic.ini` and `migrations/env.py` loading database connection from `Settings`.
  - Created baseline revision `0000_baseline.py` without premature Phase 1 tables.
- [x] **Gemini Smoke Test Script (`scripts/smoke_llm.py`)**:
  - Implemented smoke test using official `google-genai` SDK and configurable `--model`.
  - Validates native structured output using Pydantic schema `BankingSmokeResponse`.
  - Reports actual API status without fabricating success; cleanly exits with code 1 if credentials are missing or call fails.
- [x] **Quality Tooling & CI (`.github/workflows/ci.yml`, `poe check`)**:
  - Configured Poe the Poet tasks: `lint`, `format-check`, `format`, `types`, `test`, `check`, `dev`.
  - Configured `.pre-commit-config.yaml` with Ruff and file hygiene hooks.
  - Configured GitHub Actions workflow `ci.yml` running on Python 3.12 with `uv`.
- [x] **Documentation**:
  - Updated `README.md` with Windows PowerShell setup, quality check commands, and local API instructions.
  - Provided `.env.example` with safe placeholder configuration.

---

## Actual Test & Verification Results

| Tool / Check | Command | Result | Notes |
|---|---|---|---|
| Dependency Lock | `uv lock` | **PASSED** | 76 packages resolved in `uv.lock` |
| Dependency Sync | `uv sync --dev` | **PASSED** | Installed into `.venv` using Python 3.12.14 |
| Code Linting | `ruff check src tests scripts` | **PASSED** | 0 errors |
| Code Formatting | `ruff format --check src tests scripts` | **PASSED** | 24 files properly formatted |
| Static Type Check | `pyright` | **PASSED** | 0 errors, 0 warnings |
| Unit Test Suite | `pytest` | **PASSED** | 24/24 tests passed in 0.28s |
| Composite Quality | `poe check` | **PASSED** | Executed lint, format-check, types, and test successfully |
| Liveness Probe | `GET /health` | **PASSED** | HTTP 200, `{"status": "ok", "app_env": "local", "version": "0.1.0"}` |
| Readiness Probe | `GET /ready` | **PASSED** | HTTP 503, accurately reporting unconfigured Postgres & Qdrant |
| Smoke Script | `python scripts/smoke_llm.py` | **PASSED (Handled)** | Exited with code 1 and reported missing `GEMINI_API_KEY` |

---

## Windows & Environment Notes

1. **Windows Sandbox Socket Restrictions**:
   - Python's standard `asyncio` event loop uses loopback sockets/pipes for IPC. Inside Windows sandboxed command execution where loopback network is restricted, commands initiating async event loops require standard execution or bypass permissions.
2. **Neon & Qdrant Free Tier Safety**:
   - `/health` does zero I/O to avoid waking Neon compute or consuming quotas.
   - `/ready` only attempts database / vector store checks on demand with a 3-second timeout and NullPool / connection disposal.

---

## Next Phase

**Phase 1: API Skeleton, Database Models & First Migrations**
- Implement SQLAlchemy database models: `documents`, `chunks`, `query_runs`, `review_tasks`, `audit_log`.
- Generate and verify Alembic migrations against Neon Postgres `dev` branch.
- Implement database session management with connection pool pre-ping.
- Implement repository layer and repository unit/integration tests.

