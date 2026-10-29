"""SQLAlchemy 2.0 database models for Banking RAG.

Complies with ARCHITECTURE.md Section 8 (Data model):
- documents: document metadata, versioning, status
- chunks: table-safe chunk text, deterministic UUID, content hash
- query_runs: execution history, answer payloads, provenance, idempotency
- review_tasks: human-in-the-loop review tasks (answer review and ingestion approval)
- audit_log: append-only audit trail
"""

import datetime
import uuid
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

# Cross-platform JSON type: JSONB on PostgreSQL, standard JSON on SQLite
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    """Declarative base class for all Banking RAG models."""


class Document(Base):
    """Document metadata and status tracking."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        # reason for not using uuid7 is that uuid 7 support python 3.14+ and i am using python 3.12
    )
    doc_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        # Allowed values: pending, active, superseded, rejected
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Chunk.chunk_index",
    )

    __table_args__ = (
        Index("ix_documents_doc_id_status", "doc_id", "status"),
        Index("ix_documents_effective_date", "effective_date"),
    )


class Chunk(Base):
    """Text chunk derived from an ingested document."""

    __tablename__ = "chunks"

    # Deterministic UUID5 string formatted as uuid.UUID
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_chunk_index", "document_id", "chunk_index"),
        Index("ix_chunks_content_hash", "content_hash"),
    )


class QueryRun(Base):
    """Query execution run tracking question, state, answer, and provenance."""

    __tablename__ = "query_runs"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="running",
        # Allowed values: running, answered, abstained, awaiting_review, awaiting_retry, failed
    )
    answer: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    provenance: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        # Allowed values: system_verified, human_approved, human_edited, human_authored, abstained
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    review_tasks: Mapped[list["ReviewTask"]] = relationship(
        "ReviewTask",
        back_populates="query_run",
        cascade="all, delete-orphan",
    )


class ReviewTask(Base):
    """Human-in-the-loop task for ingestion approval or answer review."""

    __tablename__ = "review_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    thread_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("query_runs.thread_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        # Allowed values: ingest_approval, answer_review
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        # Allowed values: open, resolved
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    decision: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    query_run: Mapped["QueryRun"] = relationship("QueryRun", back_populates="review_tasks")

    __table_args__ = (Index("ix_review_tasks_status_kind", "status", "kind"),)


class AuditLog(Base):
    """Append-only audit log recording all critical events and human decisions."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
