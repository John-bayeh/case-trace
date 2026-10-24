"""Versioned infrastructure baseline; domain tables await P0-02 contract decisions."""

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Alembic owns the version table; no speculative domain DDL."""


def downgrade() -> None:
    """No domain tables exist in the foundation baseline."""
