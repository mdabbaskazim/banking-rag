"""Data access repositories for Banking RAG.

Complies with ARCHITECTURE.md Section 8 & 12:
- Encapsulates database queries and transactions.
- Handles idempotency, audit trail recording, and document versioning.
"""

import datetime
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from bankrag.core.errors import DatabaseError
from bankrag.db.models import AuditLog, Chunk, Document, QueryRun, ReviewTask


class DocumentRepository:
    """Repository for managing documents and their chunks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_document(
        self,
        doc_id: str,
        version: str,
        effective_date: datetime.date,
        source_filename: str,
        content_hash: str,
        status: str = "pending",
    ) -> Document:
        """Create a new document entry."""
        doc = Document(
            doc_id=doc_id,
            version=version,
            effective_date=effective_date,
            source_filename=source_filename,
            content_hash=content_hash,
            status=status,
        )
        self.session.add(doc)
        self.session.flush()
        return doc

    def get_by_id(self, doc_uuid: uuid.UUID) -> Document | None:
        """Retrieve a document by its primary key UUID."""
        return self.session.get(Document, doc_uuid)

    def get_by_content_hash(self, content_hash: str) -> Document | None:
        """Retrieve document by file content hash (for idempotency checks)."""
        stmt = select(Document).where(Document.content_hash == content_hash)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_latest_active_document(self, doc_id: str) -> Document | None:
        """Retrieve the latest active document version for a given doc_id."""
        stmt = (
            select(Document)
            .where(Document.doc_id == doc_id, Document.status == "active")
            .order_by(desc(Document.effective_date), desc(Document.created_at))
            .limit(1)
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def update_status(self, doc_uuid: uuid.UUID, new_status: str) -> Document:
        """Update status of a document."""
        doc = self.get_by_id(doc_uuid)
        if not doc:
            raise DatabaseError(f"Document {doc_uuid} not found")
        doc.status = new_status
        self.session.flush()
        return doc

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Batch insert chunks for an ingested document."""
        self.session.add_all(chunks)
        self.session.flush()

    def get_chunks_for_document(self, document_id: uuid.UUID) -> list[Chunk]:
        """Fetch all chunks for a document ordered by chunk_index."""
        stmt = select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_chunk_by_id(self, chunk_id: uuid.UUID) -> Chunk | None:
        """Fetch a single chunk by its deterministic UUID."""
        return self.session.get(Chunk, chunk_id)


class QueryRunRepository:
    """Repository for query runs and idempotency tracking."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_or_get(
        self,
        thread_id: str,
        question: str,
        idempotency_key: str | None = None,
    ) -> tuple[QueryRun, bool]:
        """Create a query run or return existing one if idempotency_key matches.

        Returns (query_run, created).
        """
        if idempotency_key:
            stmt = select(QueryRun).where(QueryRun.idempotency_key == idempotency_key)
            result = self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing, False

        query_run = QueryRun(
            thread_id=thread_id,
            question=question,
            idempotency_key=idempotency_key,
            status="running",
        )
        self.session.add(query_run)
        self.session.flush()
        return query_run, True

    def get_by_thread_id(self, thread_id: str) -> QueryRun | None:
        """Fetch query run by thread ID."""
        return self.session.get(QueryRun, thread_id)

    def update_status(
        self,
        thread_id: str,
        status: str,
        answer: dict[str, Any] | None = None,
        provenance: str | None = None,
    ) -> QueryRun:
        """Update the status and optional final answer of a run."""
        run = self.get_by_thread_id(thread_id)
        if not run:
            raise DatabaseError(f"QueryRun with thread_id {thread_id} not found")
        run.status = status
        if answer is not None:
            run.answer = answer
        if provenance is not None:
            run.provenance = provenance
        self.session.flush()
        return run


class ReviewTaskRepository:
    """Repository for managing human-in-the-loop review tasks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_task(
        self,
        thread_id: str,
        kind: str,
        reason: str,
        payload: dict[str, Any],
    ) -> ReviewTask:
        """Create a new review task."""
        task = ReviewTask(
            thread_id=thread_id,
            kind=kind,
            reason=reason,
            payload=payload,
            status="open",
        )
        self.session.add(task)
        self.session.flush()
        return task

    def get_by_id(self, task_id: uuid.UUID) -> ReviewTask | None:
        """Retrieve review task by ID."""
        return self.session.get(ReviewTask, task_id)

    def list_open_tasks(self, kind: str | None = None) -> list[ReviewTask]:
        """List open review tasks, optionally filtered by task kind."""
        stmt = select(ReviewTask).where(ReviewTask.status == "open")
        if kind:
            stmt = stmt.where(ReviewTask.kind == kind)
        stmt = stmt.order_by(desc(ReviewTask.created_at))
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def resolve_task(
        self,
        task_id: uuid.UUID,
        decision: dict[str, Any],
        resolved_by: str,
    ) -> ReviewTask:
        """Resolve an open review task."""
        task = self.get_by_id(task_id)
        if not task:
            raise DatabaseError(f"ReviewTask {task_id} not found")
        task.status = "resolved"
        task.decision = decision
        task.resolved_by = resolved_by
        task.resolved_at = datetime.datetime.now(datetime.UTC)
        self.session.flush()
        return task


class AuditLogRepository:
    """Append-only audit repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record_event(
        self,
        event: str,
        actor: str,
        payload: dict[str, Any],
        thread_id: str | None = None,
    ) -> AuditLog:
        """Append an event to the audit trail."""
        log_entry = AuditLog(
            event=event,
            actor=actor,
            payload=payload,
            thread_id=thread_id,
        )
        self.session.add(log_entry)
        self.session.flush()
        return log_entry

    def get_events_for_thread(self, thread_id: str) -> list[AuditLog]:
        """Retrieve chronological audit trail for a query or thread."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.thread_id == thread_id)
            .order_by(AuditLog.ts.asc(), AuditLog.id.asc())
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())
