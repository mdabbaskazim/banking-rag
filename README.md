# Banking RAG

Production-grade Banking RAG system with verified claims and human-in-the-loop.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for full design specifications and engineering rules.

## Quick Start (Windows PowerShell)

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```powershell
# Create virtual environment and install all dependencies
uv venv --python 3.12
uv sync --dev

# Copy example environment configuration
Copy-Item .env.example .env
```

### Quality & Tests

```powershell
# Run all quality checks (lint, format, pyright, pytest)
uv run poe check

# Run unit tests only
uv run pytest

# Run API locally
uv run poe dev
```

### Endpoints

- `GET /health`: Liveness probe (no I/O, does not touch database or network)
- `GET /ready`: Readiness probe (checks Neon Postgres and Qdrant connectivity)

