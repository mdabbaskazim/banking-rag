"""Unit tests for deterministic ID and hash generation."""

import uuid

from bankrag.core.ids import (
    generate_chunk_id,
    generate_content_hash,
    generate_thread_id,
)


def test_chunk_id_determinism() -> None:
    """Same input parameters must produce the exact same chunk ID."""
    id1 = generate_chunk_id("doc_savings", "v1.0", 0)
    id2 = generate_chunk_id("doc_savings", "v1.0", 0)
    assert id1 == id2

    # Verify it is a valid UUID
    parsed = uuid.UUID(id1)
    assert parsed.version == 5


def test_chunk_id_distinction() -> None:
    """Different chunk indices or versions must produce different IDs."""
    id1 = generate_chunk_id("doc_savings", "v1.0", 0)
    id2 = generate_chunk_id("doc_savings", "v1.0", 1)
    id3 = generate_chunk_id("doc_savings", "v2.0", 0)
    assert id1 != id2
    assert id1 != id3
    assert id2 != id3


def test_thread_id_uniqueness() -> None:
    """Thread IDs should be unique UUID4 strings."""
    t1 = generate_thread_id()
    t2 = generate_thread_id()
    assert t1 != t2
    assert uuid.UUID(t1).version == 4


def test_content_hash() -> None:
    """SHA-256 content hash must be deterministic."""
    h1 = generate_content_hash("Sample banking terms content")
    h2 = generate_content_hash("Sample banking terms content")
    assert h1 == h2
    assert len(h1) == 64
