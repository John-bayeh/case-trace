"""Persistent per-investigation conversations, independent of finalized run state."""

import sqlalchemy as sa

from alembic import op

revision = "0005_chat"
down_revision = "0004_investigation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigation_chat_messages",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id"), nullable=False
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.UniqueConstraint("investigation_id", "sequence"),
    )
    op.create_index(
        "ix_investigation_chat_messages_investigation_id",
        "investigation_chat_messages",
        ["investigation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_investigation_chat_messages_investigation_id", table_name="investigation_chat_messages"
    )
    op.drop_table("investigation_chat_messages")
