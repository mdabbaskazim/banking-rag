"""Unit tests for SQLAlchemy 2.0 database models and schema definitions."""

import datetime
import uuid

from bankrag.db.models import (
    AuditLog,
    Base,
    Chunk,
    Document,
    QueryRun,
    ReviewTask,
)


def test_tables_in_metadata() -> None:
    """Ensure all required Phase 1 tables are registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "documents",
        "chunks",
        "query_runs",
        "review_tasks",
        "audit_log",
    }
    assert expected_tables.issubset(table_names)


def test_document_model_structure() -> None:
    """Verify document table columns, keys, and indexes."""
    table = Base.metadata.tables["documents"]

    assert "id" in table.columns
    assert table.columns["id"].primary_key is True

    assert "doc_id" in table.columns
    assert "version" in table.columns
    assert "effective_date" in table.columns
    assert "source_filename" in table.columns
    assert "content_hash" in table.columns
    assert table.columns["content_hash"].unique is True

    assert "status" in table.columns
    assert "created_at" in table.columns

    # Test instantiation
    doc = Document(
        id=uuid.uuid4(),
        doc_id="savings_terms",
        version="v1.0",
        effective_date=datetime.date(2026, 1, 1),
        source_filename="01_savings_account_terms.pdf",
        content_hash="hash123",
        status="pending",
    )
    assert doc.doc_id == "savings_terms"
    assert doc.status == "pending"


def test_chunk_model_structure() -> None:
    """Verify chunk table foreign key and cascade."""
    table = Base.metadata.tables["chunks"]

    assert "id" in table.columns
    assert table.columns["id"].primary_key is True

    assert "document_id" in table.columns
    fk = next(iter(table.columns["document_id"].foreign_keys))
    assert fk.target_fullname == "documents.id"
    assert fk.ondelete == "CASCADE"

    assert "chunk_index" in table.columns
    assert "page" in table.columns
    assert "section" in table.columns
    assert "text" in table.columns
    assert "token_count" in table.columns
    assert "content_hash" in table.columns

    chunk_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk = Chunk(
        id=chunk_id,
        document_id=doc_id,
        chunk_index=0,
        page=1,
        section="Interest Rates",
        text="Savings interest is compounded quarterly.",
        token_count=10,
        content_hash="chunkhash456",
    )
    assert chunk.chunk_index == 0
    assert chunk.token_count == 10


def test_query_run_model_structure() -> None:
    """Verify query_run table primary key and idempotency key."""
    table = Base.metadata.tables["query_runs"]

    assert "thread_id" in table.columns
    assert table.columns["thread_id"].primary_key is True

    assert "question" in table.columns
    assert "status" in table.columns
    assert "answer" in table.columns
    assert "provenance" in table.columns
    assert "idempotency_key" in table.columns
    assert table.columns["idempotency_key"].unique is True

    run = QueryRun(
        thread_id="thread-xyz-123",
        question="What is the interest rate?",
        status="running",
        idempotency_key="idemp-key-1",
    )
    assert run.thread_id == "thread-xyz-123"
    assert run.status == "running"


def test_review_task_model_structure() -> None:
    """Verify review_task table structure and linkage to query_runs."""
    table = Base.metadata.tables["review_tasks"]

    assert "id" in table.columns
    assert table.columns["id"].primary_key is True

    assert "thread_id" in table.columns
    fk = next(iter(table.columns["thread_id"].foreign_keys))
    assert fk.target_fullname == "query_runs.thread_id"
    assert fk.ondelete == "CASCADE"

    assert "kind" in table.columns
    assert "status" in table.columns
    assert "reason" in table.columns
    assert "payload" in table.columns
    assert "decision" in table.columns

    task = ReviewTask(
        id=uuid.uuid4(),
        thread_id="thread-xyz-123",
        kind="answer_review",
        reason="Borderline retrieval score",
        payload={"claim": "test claim"},
        status="open",
    )
    assert task.status == "open"
    assert task.kind == "answer_review"


def test_audit_log_model_structure() -> None:
    """Verify audit_log table append-only structure."""
    table = Base.metadata.tables["audit_log"]

    assert "id" in table.columns
    assert table.columns["id"].primary_key is True

    assert "ts" in table.columns
    assert "thread_id" in table.columns
    assert "event" in table.columns
    assert "actor" in table.columns
    assert "payload" in table.columns

    entry = AuditLog(
        thread_id="thread-xyz-123",
        event="answer_verified",
        actor="system",
        payload={"score": 0.95},
    )
    assert entry.event == "answer_verified"
    assert entry.actor == "system"
