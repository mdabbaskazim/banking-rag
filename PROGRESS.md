# Banking RAG - Implementation Progress

## Status Overview

| Phase | Description | Status | Completed Date |
|---|---|---|---|
| **0** | **Foundations, Quality Tools, Core Configuration & API Skeleton** | **COMPLETED** | 2026-10-29 |
| **1** | **API skeleton, database models, first migrations** | **COMPLETED** | 2026-10-29 |
| 2 | Ingestion without LLM (Docling parse, table-safe chunking, dedupe) | Not Started | Pending Phase 1 approval |
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

- [x] **Project Packaging & Dependencies**: Configured `pyproject.toml` and verified `uv.lock` with Python 3.12 (`76 packages resolved`).
- [x] **Core Configuration (`src/bankrag/core/config.py`)**: `Settings` class with full Section 11 parameters, cloud credential validation, and topic parsing.
- [x] **Structured Logging (`src/bankrag/core/logging.py`)**: Structured JSON logging to stdout with automated secret redaction and Rule 10 question anonymization.
- [x] **Core Errors & IDs (`src/bankrag/core/errors.py`, `src/bankrag/core/ids.py`)**: Typed exceptions and deterministic UUID5 chunk ID generation.
- [x] **Provider Interfaces & Fakes (`src/bankrag/providers/`)**: `LLMProvider`, `VectorStoreProvider`, `RateLimiterProvider` and in-memory fakes.
- [x] **FastAPI Application & Endpoints (`src/bankrag/api/`)**: `/health` (zero I/O) and `/ready` probes.
- [x] **Alembic Baseline Migration**: `0000_baseline.py` initial revision.
- [x] **Gemini Smoke Test Script**: `scripts/smoke_llm.py` structured output test.

---

## Phase 1: Database Models & Migrations

### Completed Work

- [x] **SQLAlchemy 2.0 Database Models (`src/bankrag/db/models.py`)**:
  - `documents`: Metadata, versioning, status (`pending`, `active`, `superseded`, `rejected`), unique `content_hash`, indexes.
  - `chunks`: Table-safe chunk text, deterministic UUID5 primary key, foreign key to `documents.id` with `CASCADE`, `content_hash`.
  - `query_runs`: Execution run tracking, status (`running`, `answered`, `abstained`, `awaiting_review`, `awaiting_retry`, `failed`), `answer` (JSON), `provenance`, and unique `idempotency_key`.
  - `review_tasks`: Human-in-the-loop task queue (`ingest_approval`, `answer_review`), status (`open`, `resolved`), reason, payload, and decision tracking.
  - `audit_log`: Append-only audit trail capturing chronological events, actors, and JSON payloads.
- [x] **Database Session Management (`src/bankrag/db/session.py`)**:
  - Implemented `get_engine`, `get_session_factory`, and `get_db_session` dependency.
  - Added connection pool pre-ping (`pool_pre_ping=True`) for Neon scale-to-zero cold-start safety.
  - Clean URL normalization with PostgreSQL psycopg driver support.
- [x] **Data Access Repositories (`src/bankrag/db/repositories.py`)**:
  - `DocumentRepository`: Create, retrieve by ID / content hash, latest active version lookup, status update, and chunk batching.
  - `QueryRunRepository`: Idempotency handling (`create_or_get`), status updates, provenance, and final answer storage.
  - `ReviewTaskRepository`: Task creation, open task listings (filtered by kind), and resolution recording.
  - `AuditLogRepository`: Append-only audit logging and thread-level event history.
- [x] **Alembic Migration Setup & Live Verification (`migrations/`)**:
  - Updated `migrations/env.py` to link `Base.metadata`.
  - Created migration revision `0001_phase1_tables.py` generating all 5 tables, foreign keys, and indexes.
  - Verified static SQL generation via `alembic upgrade head --sql`.
  - Applied migration to Neon database: upgraded `0000_baseline` -> `0001_phase1_tables (head)`.
  - Verified live tables on Neon: `alembic_version`, `documents`, `chunks`, `query_runs`, `review_tasks`, `audit_log`.
- [x] **Focused Offline Tests (`tests/unit/`)**:
  - `tests/unit/test_db_models.py`: Structural, column, nullability, unique constraint, and relationship verification.
  - `tests/unit/test_repositories.py`: Complete mock-based verification of repository methods and idempotency.

---

## Actual Test & Verification Results

| Tool / Check | Command | Result | Notes |
|---|---|---|---|
| Code Linting | `ruff check src tests migrations scripts` | **PASSED** | 0 errors |
| Code Formatting | `ruff format --check src tests migrations scripts` | **PASSED** | 33 files formatted |
| Static Type Check | `pyright` | **PASSED** | 0 errors, 0 warnings |
| Unit Test Suite | `pytest` | **PASSED** | 37/37 tests passed in 0.60s |
| Composite Quality | `poe check` | **PASSED** | All quality checks passed |
| Alembic Static SQL | `alembic upgrade head --sql` | **PASSED** | Generated DDL for all 5 tables offline |
| Neon Migration | `alembic upgrade head` | **PASSED** | Successfully applied to Neon `0001_phase1_tables (head)` |
| Neon Schema Inspection | Database Inspector | **PASSED** | Verified all 5 tables, PKs, FKs, and indexes in Neon |
| DB Readiness Probe | `check_database_health()` | **PASSED** | Verified live connection returns `status: healthy` |

---

## Windows & Free-Tier Safety Notes

1. **Zero Cloud Dependency in Tests**: Unit tests run 100% offline with zero Neon credentials needed.
2. **Neon Connection Safety**: Direct connection used with `connect_timeout=3` and threadpool execution to prevent Windows Proactor event loop conflicts.
3. **Local PDF Isolation**: Local banking PDFs in `Bank_pdf/` remain local and unmodified.

---

## Next Phase

**Phase 2: Ingestion without LLM**
- Docling-based PDF parsing with table preservation.
- Chunking strategy preserving table structure and section headers.
- Deduplication via content hashing.
- Batch storage of documents and chunks into Postgres.
- CLI script for folder ingestion (`scripts/ingest_folder.py`).
