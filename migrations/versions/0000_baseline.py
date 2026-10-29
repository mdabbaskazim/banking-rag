"""Baseline initial migration for Phase 0.

Revision ID: 0000_baseline
Revises:
Create Date: 2026-10-28 23:30:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0000_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Baseline migration - no tables created in Phase 0."""
    pass


def downgrade() -> None:
    """Baseline rollback."""
    pass
