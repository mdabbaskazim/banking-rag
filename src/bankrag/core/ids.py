"""ID generation utilities for Banking RAG.

Complies with ARCHITECTURE.md Section 7:
- Chunk IDs are deterministic UUID5 derived from a fixed namespace and
  (doc_id + version + chunk_index).
- Thread IDs and Run IDs are standard UUID4 strings.
- Content hashes use SHA-256.
"""

import hashlib
import uuid

# Fixed namespace UUID for Banking RAG chunks to guarantee cross-system reproducibility
BANKRAG_CHUNK_NAMESPACE = uuid.UUID("a7e8e50b-3310-4824-9b88-12093557e05a")


def generate_chunk_id(doc_id: str, version: str, chunk_index: int) -> str:
    """Generate a deterministic UUID5 chunk id from doc_id, version, and chunk_index."""
    seed = f"{doc_id}:{version}:{chunk_index}"
    return str(uuid.uuid5(BANKRAG_CHUNK_NAMESPACE, seed))


def generate_thread_id() -> str:
    """Generate a unique thread identifier for a query run or workflow session."""
    return str(uuid.uuid4())


def generate_content_hash(content: str | bytes) -> str:
    """Compute standard SHA-256 hash for document or chunk content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()
