# Banking RAG: Architecture

Version 1.0. Status: approved design, nothing built yet.

> **For AI coding agents:** read section 1 (rules), the section for the phase you were given, and `PROGRESS.md`. Do not read the whole repo. Implement only the phase you were given. Ask before adding any dependency not listed in section 3.

**Index:** 1 Goals and rules · 2 Constraints · 3 Tech stack · 4 System overview · 5 Repository layout · 6 Query graph · 7 Ingestion graph · 8 Data model · 9 Reliability · 10 Human in the loop · 11 Configuration · 12 Engineering rules · 13 Testing · 14 Phases · 15 Open questions

---

## 1. Goals and rules

### Goals

- **G1. No unsupported claim reaches a user.** Every statement is a verified claim with a citation, or the system abstains or escalates to a human.
- **G2. Fault tolerance.** A crash, timeout or quota error resumes or degrades safely. No work is lost.
- **G3. Long pause and resume with a human in the loop.** A run can wait for days without holding a process, and resumes from Postgres.
- **G4. Zero cost.** Free tiers and open-source tools only.
- **G5. Production-grade design on a laptop.** Scaling later is a configuration change, not a rewrite.
- **G6. No Docker until Phase 10,** but the code is Docker-ready from day one (section 12).

### Non-negotiable rules

1. **R1.** The text shown to the user is rendered by code from verified claims. It is never free LLM text.
2. **R2.** Abstain by default. When evidence or verification is weak, abstain or escalate. Never guess.
3. **R3.** Every external call has a timeout, a retry policy and a rate limit.
4. **R4.** Every provider (LLM, embedder, vector store, reranker, entailment) sits behind an interface with a fake implementation.
5. **R5.** Configuration comes only from environment variables, read in one `Settings` class.
6. **R6.** Secrets are never logged and never committed.
7. **R7.** Tests never call a real LLM or cloud service, except tests marked `integration` or `smoke`.
8. **R8.** Postgres is the source of truth for chunks. Qdrant is a derived index that can be rebuilt from Postgres.

---

## 2. Constraints

| Area | Constraint | Consequence |
|---|---|---|
| Cost | Zero. Free tiers only. | No paid services, no paid API keys. |
| Laptop | Intel i5-13420H, 16 GB RAM, no Docker until Phase 10 | CPU-only models, no local LLM, no local databases. |
| LLM (Gemma via API) | 30 requests/min, 16,000 tokens/min, 14,400 requests/day (verify in AI Studio) | A client-side limiter is mandatory. About 2 queries/min at 2 calls each. Keep prompts small. |
| Qdrant Cloud free | Single node, 0.5 vCPU, 1 GB RAM, 4 GB disk | Small prefetch limits. Multivectors on disk or deferred. The cluster may be suspended or deleted if idle, so the index must be rebuildable (R8). |
| Neon free | 100 CU-hours/project/month, 1 GB storage/project, scale-to-zero after 5 min, 10 branches/project | Do not keep the database awake. Keep checkpoints small. Use a `dev` branch. Expect cold starts. |
| Data | Synthetic banking PDFs only | Never upload real customer data to free tiers. |

All limits live in configuration (section 11), never hardcoded.

---

## 3. Tech stack

"Phase" is when a dependency is first installed. Do not install ahead of the phase.

| Layer | Choice | Phase |
|---|---|---|
| Language and env | Python 3.12, `uv`, committed `uv.lock` | 0 |
| API | FastAPI, Uvicorn, `pydantic`, `pydantic-settings` | 0 |
| Logging | `structlog` (JSON to stdout) | 0 |
| Relational | Neon Postgres, SQLAlchemy 2, Alembic, `psycopg` 3 with pool | 0 |
| Vector store | Qdrant Cloud, `qdrant-client` | 0 (client), 3 (use) |
| LLM client | `google-genai` SDK directly. Instructor added only if native structured output is weak. | 0 |
| Retries | `tenacity` | 0 |
| Quality tools | `ruff`, `pyright`, `pytest`, `pytest-asyncio`, `hypothesis`, `httpx`, `pre-commit`, `poethepoet` | 0 |
| Parsing | Docling | 2 |
| Embeddings | BGE-M3 via `FlagEmbedding`, CPU `torch` | 3 |
| Orchestration and HITL | LangGraph, `langgraph-checkpoint-postgres` | 4 (graph), 6 (durability) |
| Entailment | Vectara HHEM (local, verify licence) | 5 |
| Reviewer UI | Gradio | 6 |
| Background jobs | Procrastinate (Postgres-backed) | 7 |
| Evals | DeepEval, Ragas (separate `eval` dependency group) | 8 |
| Tracing | `structlog` now, Langfuse Cloud free plan | 9 |
| CI | GitHub Actions | 0 |
| Containers | Docker, Docker Compose | 10 |

Dependency groups in `pyproject.toml`: `runtime`, `dev`, `eval`. The container image installs `runtime` only.

Dropped on purpose: Ollama, pgvector, Postgres full-text search, Redis, Celery, `langchain-google-genai`, self-hosted Langfuse.

---

## 4. System overview

```
Client / Reviewer UI (Gradio)
            |
         FastAPI ----------- Postgres (Neon)
            |                 checkpoints, documents, chunks,
            |                 review_tasks, audit_log, query_runs
            |
     LangGraph runtime ------ Qdrant Cloud
     (in-process tasks;       collection alias "chunks"
      worker from Phase 7)    dense + sparse (+ colbert later)
            |
   Providers behind interfaces
   LLMClient (Gemma API) · Embedder (BGE-M3, local)
   Entailment (HHEM, local) · VectorStore · RateLimiter
```

FastAPI only accepts requests, starts or resumes runs, and reads state. Work happens inside graph runs.

---

## 5. Repository layout

```
repo/
├── ARCHITECTURE.md
├── PROGRESS.md
├── README.md
├── pyproject.toml            # uv, groups: runtime / dev / eval, poe tasks, ruff, pyright
├── uv.lock
├── .env.example
├── .pre-commit-config.yaml
├── alembic.ini
├── migrations/
├── src/bankrag/
│   ├── core/                 # config.py (Settings), logging.py, errors.py, ids.py
│   ├── api/                  # main.py, routes_health.py, routes_query.py,
│   │                         # routes_ingest.py, routes_review.py
│   ├── providers/            # interfaces.py + llm/, embeddings/, vectorstore/,
│   │                         # entailment/, ratelimit/, fakes/
│   ├── ingestion/            # parse.py, chunk.py, pipeline.py, graph.py (Phase 6)
│   ├── retrieval/            # hybrid.py, gate.py
│   ├── graph/                # state.py, nodes/, routing.py, build.py
│   ├── verification/         # quote.py, numeric.py, entailment.py, renderer.py
│   ├── db/                   # models.py, session.py, repositories.py
│   ├── review/               # service.py (create, resolve, resume)
│   ├── worker/               # tasks.py (Phase 7)
│   └── audit/                # events.py
├── scripts/                  # smoke_llm.py, ingest_folder.py, reindex.py
├── evals/                    # golden_set.jsonl, unanswerable.jsonl, run_evals.py
├── tests/{unit,integration,smoke}/
└── .github/workflows/ci.yml
```

No `Dockerfile` or `docker-compose.yml` before Phase 10.

---

## 6. Query graph (Phases 4 to 7)

### Flow

```
guard -> normalize -> retrieve -> gate
gate: strong evidence    -> generate
gate: borderline         -> escalate (interrupt)
gate: weak or none       -> abstain
generate -> verify_deterministic -> verify_entailment -> route
route: all claims pass   -> render -> finalize
route: some fail, tries left (max 2) -> generate (with failure feedback)
route: still failing     -> escalate (interrupt)
finalize / abstain / escalate result -> audit
```

### Nodes

| Node | What it does | LLM call? |
|---|---|---|
| guard | Length limit, empty check, topic check against `RISKY_TOPICS` (those go to escalate). | No |
| normalize | Deterministic cleanup. No LLM rewrite by default (saves tokens). | No |
| retrieve | Qdrant hybrid search, filtered to active, latest-version chunks. | No |
| gate | Compares top score and chunk count with thresholds. Strong, borderline or weak. | No |
| generate | Structured output (below) from the top K chunks. Enforces the per-query token budget. | Yes |
| verify_deterministic | Quote check and numeric check (below). | No |
| verify_entailment | HHEM score for each (quote, claim). | No (local model) |
| route | Applies the policy above. | No |
| render | Builds the final text from verified claims plus citations (R1). | No |

### Structured answer schema

```
Answer:
  abstain: bool
  abstain_reason: str | null
  claims: list[Claim]
Claim:
  text: str          # one factual statement
  chunk_id: str      # a chunk id from the provided evidence only
  quote: str         # verbatim text copied from that chunk
```

### Verification rules

1. **Chunk check:** `chunk_id` must be one of the chunks given to the model.
2. **Quote check:** after normalizing whitespace, case, quotes and dashes, `quote` must be a substring of the chunk text.
3. **Numeric check:** every number, percentage, currency amount and date in `claim.text` must appear in `quote`. Compare digits only, so `1,00,000`, `100000` and `1 lakh` rules are handled by a documented normalizer with tests.
4. **Entailment check:** HHEM score for (`quote` as premise, `claim.text` as hypothesis) must be at least `HHEM_THRESHOLD`.
5. **Version check:** if retrieved chunks come from two versions of the same document, prefer the latest `effective_date`. If both versions are cited, escalate.
6. A claim that fails any check is not shown. Retry with feedback naming the failed check, at most `MAX_VERIFY_RETRIES`. If the answer has no passing claims, abstain or escalate.

### Run state (LangGraph)

`thread_id`, `question`, `normalized_question`, `retrieved` (chunk ids + scores only, not text), `gate_result`, `draft` (Answer), `verification` (per claim results), `attempts`, `tokens_used`, `status`, `final_answer`, `provenance`. Keep state small. Fetch chunk text from Postgres when needed.

### Provenance values

`system_verified`, `human_approved`, `human_edited`, `human_authored`, `abstained`.

---

## 7. Ingestion graph (Phases 2, 3, 6)

```
parse (Docling) -> chunk -> dedupe -> store chunks (Postgres, status pending)
 -> embed (BGE-M3, batched) -> approval (interrupt) -> index (Qdrant upsert)
 -> activate document, supersede older versions -> audit
```

- Phase 2 builds these as plain functions with a CLI. Phase 6 wraps them in a graph with the approval interrupt.
- **Chunking:** keep tables whole. Split prose by section, with a maximum token size. Store `page`, `section`, `chunk_index`.
- **Idempotency:** `content_hash` of the file and per-chunk hash. Re-ingesting the same file changes nothing.
- **Chunk ids:** `uuid5(namespace, doc_id + version + chunk_index)`, used in both Postgres and Qdrant.
- **Versioning:** a new version of a `doc_id` stays `pending` until approved. On activation, the older version becomes `superseded` and its Qdrant points get `is_active=false`.
- **Rebuild:** `scripts/reindex.py` re-embeds all chunks from Postgres into a new collection (`chunks_v2`) and swaps the `chunks` alias.

---

## 8. Data model

### Postgres (Neon)

| Table | Key columns |
|---|---|
| `documents` | `id`, `doc_id`, `version`, `effective_date`, `source_filename`, `content_hash` (unique), `status` (`pending`, `active`, `superseded`, `rejected`), `created_at` |
| `chunks` | `id` (deterministic uuid), `document_id`, `chunk_index`, `page`, `section`, `text`, `token_count`, `content_hash` |
| `query_runs` | `thread_id`, `question`, `status` (`running`, `answered`, `abstained`, `awaiting_review`, `awaiting_retry`, `failed`), `answer` (jsonb), `provenance`, `created_at`, `updated_at`, `idempotency_key` (unique) |
| `review_tasks` | `id`, `thread_id`, `kind` (`ingest_approval`, `answer_review`), `status` (`open`, `resolved`), `reason`, `payload` (jsonb), `decision` (jsonb), `created_at`, `resolved_at`, `resolved_by` |
| `audit_log` | `id`, `ts`, `thread_id`, `event`, `actor`, `payload` (jsonb). Append-only. |
| LangGraph checkpoint tables | Created and managed by `langgraph-checkpoint-postgres`. Do not edit by hand. |

### Qdrant

- Collection `chunks_v1`, reached through the alias `chunks`.
- Named vectors: `dense` (1024, cosine), `sparse` (BGE-M3 lexical weights), `colbert` (1024, multivector, MAX_SIM, `on_disk`, no HNSW). Create `colbert` only if Phase 3 evals show a gain.
- Payload: `chunk_id`, `doc_id`, `version`, `effective_date`, `page`, `section`, `is_active`. Payload indexes on `doc_id`, `is_active`, `effective_date`.
- Query: prefetch dense and sparse (each `PREFETCH_LIMIT`), fuse with RRF, return top `RETRIEVE_K`, then keep `LLM_CONTEXT_K` for the LLM.

---

## 9. Reliability

| Failure | Behavior |
|---|---|
| LLM 429 or quota | Wait for `Retry-After` if within the budget. Otherwise checkpoint, set `awaiting_retry`, retry later. |
| LLM timeout or 5xx | `tenacity`: 3 tries, exponential backoff with jitter. Then the circuit breaker opens. |
| Invalid structured output | Up to `MAX_VERIFY_RETRIES` re-asks (they count toward the token budget), then escalate. |
| Qdrant unavailable | 3 retries, then `failed` with a retryable flag. Never answer without evidence. |
| Neon cold start | Connection pool pre-ping and retry on connection errors. |
| Crash mid-run | On startup, reconcile `query_runs` stuck in `running` and resume them from the checkpoint. |
| Duplicate request | `idempotency_key` returns the same `thread_id`. |
| Per-query token budget exceeded | Abstain with a clear reason. |

**Rate limiter:** token bucket with two buckets (requests/min and tokens/min). Estimate tokens before each call (characters / 4), reconcile with the actual usage in the response. In-process now. The interface allows a Postgres or Redis backing later for multiple workers.

**Circuit breaker:** small in-house class (about 40 lines): closed, open after N consecutive failures, half-open after a cooldown.

**Neon compute:** nothing may poll the database continuously. `/health` does no I/O. `/ready` checks services only when called. The Phase 7 worker runs only on demand.

---

## 10. Human in the loop

- **Triggers:** borderline gate, failed verification after retries, risky topic, conflicting versions, ingestion of a new document version.
- **Mechanism:** a node calls `interrupt(payload)`. LangGraph checkpoints to Postgres and the run stops holding any process. A `review_tasks` row is created.
- **Payload (answer review):** question, draft claims, failed checks, evidence chunks with ids.
- **API:**
  - `GET /reviews?status=open` lists tasks.
  - `GET /reviews/{id}` shows the full payload.
  - `POST /reviews/{id}/resume` with a decision resumes with `Command(resume=decision)`.
- **Decisions:** `approve` (publish the draft, provenance `human_approved`), `edit` (reviewer supplies claims with citations, which still pass the deterministic checks, provenance `human_edited`), `reject` (abstain with a message), `add_context` (reviewer note, re-run generation).
- **Ingestion approval:** `approve` activates the document, `reject` marks it `rejected`.
- **Feedback loop:** every resolved answer review can be exported to `evals/golden_set.jsonl`.
- **Audit:** every escalation and decision is written to `audit_log` with the reviewer id.

---

## 11. Configuration

All variables are read by `core/config.py`. `.env.example` lists them with safe placeholders.

| Variable | Meaning | Default |
|---|---|---|
| `APP_ENV` | `local`, `test`, `cloud` | `local` |
| `LOG_LEVEL` | Log level | `INFO` |
| `DATABASE_URL` | Neon **direct** connection (migrations, checkpointer, worker) | required |
| `DATABASE_POOLED_URL` | Neon pooled connection (optional, request queries) | empty |
| `QDRANT_URL`, `QDRANT_API_KEY` | Qdrant Cloud | required |
| `QDRANT_COLLECTION_ALIAS` | Alias used by the app | `chunks` |
| `GEMINI_API_KEY` | Google AI Studio key | required |
| `LLM_MODEL` | Exact model id from AI Studio | required |
| `LLM_RPM`, `LLM_TPM`, `LLM_RPD` | Rate limits | 30, 16000, 14400 |
| `LLM_TIMEOUT_S` | Per-call timeout | 60 |
| `LLM_MAX_QUERY_TOKENS` | Token budget per query | 8000 |
| `FAKE_LLM` | Use the fake LLM | `false` |
| `EMBED_MODEL` | Embedding model | `BAAI/bge-m3` |
| `HF_HOME` | Model cache location | `./.cache/hf` |
| `PREFETCH_LIMIT`, `RETRIEVE_K`, `LLM_CONTEXT_K` | Retrieval sizes | 30, 10, 5 |
| `GATE_STRONG`, `GATE_WEAK` | Gate thresholds (calibrate in Phase 4) | placeholders |
| `HHEM_THRESHOLD` | Entailment threshold (calibrate in Phase 5) | placeholder |
| `MAX_VERIFY_RETRIES` | Re-asks after failed verification | 2 |
| `RISKY_TOPICS` | Comma-separated topics that always escalate | `dispute,fraud liability,eligibility` |

---

## 12. Engineering rules (Docker-ready from day one)

1. Configuration only through `Settings` (R5). No hardcoded hosts, paths or keys.
2. No state written to local disk except caches, and the cache path is configurable (`HF_HOME`).
3. Logs go to stdout as structured JSON.
4. Graceful shutdown: on SIGTERM, close pools and checkpoint in-flight runs.
5. One entrypoint per process: `uvicorn bankrag.api.main:app` and `python -m bankrag.worker`.
6. Dependencies pinned through `uv.lock`, grouped as `runtime`, `dev`, `eval`.
7. Type hints everywhere. `ruff` and `pyright` must pass.
8. No cross-platform assumptions: the project must run on Windows and Linux. Use `poethepoet` tasks, not a Makefile.
9. Every endpoint has a test. Every verifier has property tests (`hypothesis`).
10. Never log secrets, questions are logged only as hashes plus length at `INFO`.

---

## 13. Testing

| Level | Scope | Uses |
|---|---|---|
| `unit` | Verifiers, routing, gate, chunking, config, rate limiter, circuit breaker | Fakes only. Runs on every save and in CI. |
| `integration` | Alembic migrations, `PostgresSaver`, Qdrant, interrupt and resume | Neon `dev` branch, Qdrant Cloud or local mode. Run on purpose. |
| `smoke` | Ingest one PDF and ask one question end to end | Real services. Run before merging a phase. |
| `evals` | Golden set: answerable, unanswerable, multi-document, numeric | CI gate on faithfulness, citation accuracy, abstain rate. |

Mark tests with `@pytest.mark.integration` and `@pytest.mark.smoke`. The default `pytest` run skips them.

---

## 14. Phases

Each phase ends with a commit, a green `poe check`, and an update to `PROGRESS.md`.

| Phase | Scope | Done when |
|---|---|---|
| 0 | Foundations: repo, `uv`, quality tools, `Settings`, logging, `/health`, `/ready`, Alembic baseline, LLM smoke script, CI | `poe check` passes. `/ready` reports Neon and Qdrant. The smoke script prints a structured-output result. |
| 1 | API skeleton, database models, first migrations (`documents`, `chunks`, `query_runs`, `review_tasks`, `audit_log`) | Migrations apply to the Neon `dev` branch. Repository tests pass. |
| 2 | Ingestion without LLM: Docling parse, table-safe chunking, dedupe, store in Postgres, CLI | The 10 banking PDFs load. Re-ingest changes nothing. |
| 3 | BGE-M3 embeddings, Qdrant collection and alias, hybrid retrieval, `/search` | 10 hand-written questions return the right chunk in the top 5. |
| 4 | Query graph happy path: gate, generate, render. Rate limiter and fake LLM. | Answerable questions get cited answers. Out-of-scope questions abstain. |
| 5 | Verification: quote, numeric, entailment, retry routing | Deliberately wrong answers all fail verification (unit tests). |
| 6 | Durability and HITL: checkpointer, `interrupt`, review API, Gradio reviewer, ingestion approval | Escalate, stop the server, restart, resume: succeeds. |
| 7 | Reliability: `RetryPolicy`, circuit breaker, Procrastinate worker, chaos tests | Quota exhaustion and LLM failure degrade to `awaiting_retry`, never to a crash or a guess. |
| 8 | Evals and CI gates | A deliberately bad change turns CI red. |
| 9 | Observability: Langfuse Cloud, audit views | A trace shows each node, tokens and verification results for one query. |
| 10 | Docker: multi-stage `Dockerfile`, `.dockerignore`, `docker-compose.yml`, CI image build, `SCALING.md` | `docker compose up` runs the API and a worker. CI builds the image and passes the smoke test. |

---

## 15. Open questions

Record answers in `PROGRESS.md` when resolved.

1. Does the Gemma model on the API support native structured output (JSON mode or a response schema)? Phase 0 smoke script tests this. If not, use prompt-for-JSON plus Pydantic validation, or Instructor.
2. What is the exact model id string for `LLM_MODEL`?
3. Does Qdrant local mode support sparse and multivector vectors? Needed for unit tests.
4. What is the Neon minimum compute size on this account?
5. Do Docling and `FlagEmbedding` install and run on the developer's OS (Windows or Linux)? Check at the start of Phase 2 and 3.
6. Is the HHEM licence and size acceptable? Confirm in Phase 5.
7. Which Qdrant Cloud Inference models are offered (is BGE-M3 among them)? If not, embeddings stay local.
