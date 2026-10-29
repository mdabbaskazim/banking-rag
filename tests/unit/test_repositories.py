"""Unit tests for repository data access logic."""

import datetime
import uuid
from unittest.mock import MagicMock

from bankrag.core.errors import DatabaseError
from bankrag.db.models import Document, QueryRun, ReviewTask
from bankrag.db.repositories import (
    AuditLogRepository,
    DocumentRepository,
    QueryRunRepository,
    ReviewTaskRepository,
)


def test_document_repository_create_and_get() -> None:
    session = MagicMock()
    repo = DocumentRepository(session)

    doc = repo.create_document(
        doc_id="savings_doc",
        version="v1.0",
        effective_date=datetime.date(2026, 1, 1),
        source_filename="savings.pdf",
        content_hash="hash_abc_123",
    )

    assert doc.doc_id == "savings_doc"
    assert doc.status == "pending"
    session.add.assert_called_once_with(doc)
    session.flush.assert_called_once()

    target_id = uuid.uuid4()
    session.get.return_value = doc
    retrieved = repo.get_by_id(target_id)
    assert retrieved is doc
    session.get.assert_called_once_with(Document, target_id)


def test_document_repository_update_status_not_found() -> None:
    import pytest

    session = MagicMock()
    session.get.return_value = None
    repo = DocumentRepository(session)

    with pytest.raises(DatabaseError, match="not found"):
        repo.update_status(uuid.uuid4(), "active")


def test_document_repository_update_status_success() -> None:
    session = MagicMock()
    doc = Document(id=uuid.uuid4(), doc_id="d1", status="pending")
    session.get.return_value = doc
    repo = DocumentRepository(session)

    updated = repo.update_status(doc.id, "active")
    assert updated.status == "active"
    session.flush.assert_called_once()


def test_query_run_repository_idempotency() -> None:
    session = MagicMock()
    repo = QueryRunRepository(session)

    # 1. Existing run found via idempotency_key
    existing_run = QueryRun(
        thread_id="thread-existing",
        question="What is the minimum balance?",
        idempotency_key="key-123",
        status="answered",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_run
    session.execute.return_value = mock_result

    run, created = repo.create_or_get(
        thread_id="thread-new",
        question="What is the minimum balance?",
        idempotency_key="key-123",
    )
    assert created is False
    assert run.thread_id == "thread-existing"

    # 2. No existing run found
    mock_result.scalar_one_or_none.return_value = None
    run2, created2 = repo.create_or_get(
        thread_id="thread-new-2",
        question="What is the minimum balance?",
        idempotency_key="key-456",
    )
    assert created2 is True
    assert run2.thread_id == "thread-new-2"
    session.add.assert_called_with(run2)


def test_query_run_repository_update_status() -> None:
    session = MagicMock()
    run = QueryRun(thread_id="thread-1", question="Q", status="running")
    session.get.return_value = run
    repo = QueryRunRepository(session)

    updated = repo.update_status(
        thread_id="thread-1",
        status="answered",
        answer={"claims": []},
        provenance="system_verified",
    )
    assert updated.status == "answered"
    assert updated.provenance == "system_verified"
    assert updated.answer == {"claims": []}


def test_review_task_repository_create_and_resolve() -> None:
    session = MagicMock()
    repo = ReviewTaskRepository(session)

    task_id = uuid.uuid4()
    task = ReviewTask(
        id=task_id,
        thread_id="thread-1",
        kind="answer_review",
        reason="Low score",
        payload={"score": 0.3},
        status="open",
    )
    session.get.return_value = task

    resolved = repo.resolve_task(
        task_id=task_id,
        decision={"action": "approve"},
        resolved_by="analyst_alice",
    )
    assert resolved.status == "resolved"
    assert resolved.decision == {"action": "approve"}
    assert resolved.resolved_by == "analyst_alice"
    assert resolved.resolved_at is not None


def test_audit_log_repository_record_event() -> None:
    session = MagicMock()
    repo = AuditLogRepository(session)

    entry = repo.record_event(
        event="gate_evaluated",
        actor="system",
        payload={"result": "strong_evidence"},
        thread_id="thread-100",
    )
    assert entry.event == "gate_evaluated"
    assert entry.actor == "system"
    assert entry.thread_id == "thread-100"
    session.add.assert_called_once_with(entry)
    session.flush.assert_called_once()
