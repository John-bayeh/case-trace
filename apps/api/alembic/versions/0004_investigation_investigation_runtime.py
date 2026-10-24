"""investigation_runtime

Revision ID: 0004_investigation
Revises: 0003_clinical_reports
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_investigation"
down_revision = "0003_clinical_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reviewed: investigation-only tables, source tables unchanged; explicit FK/drop order.
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("requested_by", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','running','completed',"
            "'completed_with_limitations','failed','cancelled')",
            name=op.f("ck_investigations_status"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["case_datasets.id"],
            name=op.f("fk_investigations_dataset_id_case_datasets"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_investigations_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigations")),
        sa.UniqueConstraint("external_id", name=op.f("uq_investigations_external_id")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_investigations_idempotency_key")),
    )
    with op.batch_alter_table("investigations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_investigations_patient_id"), ["patient_id"], unique=False
        )

    op.create_table(
        "agent_executions",
        sa.Column("agent_key", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("task_summary", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_agent_executions_investigation_id_investigations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_executions")),
        sa.UniqueConstraint(
            "investigation_id",
            "agent_key",
            "attempt",
            name=op.f("uq_agent_executions_investigation_id"),
        ),
    )
    with op.batch_alter_table("agent_executions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_agent_executions_investigation_id"), ["investigation_id"], unique=False
        )

    op.create_table(
        "evidence_refs",
        sa.Column("anchor", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_evidence_refs_investigation_id_investigations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_refs")),
    )
    with op.batch_alter_table("evidence_refs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_evidence_refs_investigation_id"), ["investigation_id"], unique=False
        )

    op.create_table(
        "findings",
        sa.Column("logical_key", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_findings_investigation_id_investigations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_findings")),
        sa.UniqueConstraint(
            "investigation_id", "logical_key", name=op.f("uq_findings_investigation_id")
        ),
    )
    with op.batch_alter_table("findings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_findings_investigation_id"), ["investigation_id"], unique=False
        )

    op.create_table(
        "investigation_events",
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_investigation_events_investigation_id_investigations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_events")),
        sa.UniqueConstraint(
            "investigation_id", "sequence", name=op.f("uq_investigation_events_investigation_id")
        ),
    )
    with op.batch_alter_table("investigation_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_investigation_events_investigation_id"),
            ["investigation_id"],
            unique=False,
        )

    op.create_table(
        "investigation_stages",
        sa.Column("stage_key", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_investigation_stages_investigation_id_investigations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_stages")),
        sa.UniqueConstraint(
            "investigation_id",
            "stage_key",
            "attempt",
            name=op.f("uq_investigation_stages_investigation_id"),
        ),
    )
    with op.batch_alter_table("investigation_stages", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_investigation_stages_investigation_id"),
            ["investigation_id"],
            unique=False,
        )

    op.create_table(
        "reports",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("body_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_reports_investigation_id_investigations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint(
            "investigation_id", "version", name=op.f("uq_reports_investigation_id")
        ),
    )
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reports_investigation_id"), ["investigation_id"], unique=False
        )

    op.create_table(
        "finding_evidence_links",
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_ref_id", sa.Uuid(), nullable=False),
        sa.Column("relationship", sa.String(), nullable=False),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"],
            ["evidence_refs.id"],
            name=op.f("fk_finding_evidence_links_evidence_ref_id_evidence_refs"),
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.id"],
            name=op.f("fk_finding_evidence_links_finding_id_findings"),
        ),
        sa.PrimaryKeyConstraint(
            "finding_id", "evidence_ref_id", "relationship", name=op.f("pk_finding_evidence_links")
        ),
    )
    op.create_table(
        "tool_calls",
        sa.Column("agent_execution_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("sanitized_args", sa.JSON(), nullable=False),
        sa.Column("result_refs", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_execution_id"],
            ["agent_executions.id"],
            name=op.f("fk_tool_calls_agent_execution_id_agent_executions"),
        ),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name=op.f("fk_tool_calls_investigation_id_investigations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_calls")),
    )
    with op.batch_alter_table("tool_calls", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_tool_calls_investigation_id"), ["investigation_id"], unique=False
        )


def downgrade() -> None:
    # Reviewed: investigation-only tables, source tables unchanged; explicit FK/drop order.
    with op.batch_alter_table("tool_calls", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tool_calls_investigation_id"))

    op.drop_table("tool_calls")
    op.drop_table("finding_evidence_links")
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reports_investigation_id"))

    op.drop_table("reports")
    with op.batch_alter_table("investigation_stages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_investigation_stages_investigation_id"))

    op.drop_table("investigation_stages")
    with op.batch_alter_table("investigation_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_investigation_events_investigation_id"))

    op.drop_table("investigation_events")
    with op.batch_alter_table("findings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_findings_investigation_id"))

    op.drop_table("findings")
    with op.batch_alter_table("evidence_refs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_evidence_refs_investigation_id"))

    op.drop_table("evidence_refs")
    with op.batch_alter_table("agent_executions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_agent_executions_investigation_id"))

    op.drop_table("agent_executions")
    with op.batch_alter_table("investigations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_investigations_patient_id"))

    op.drop_table("investigations")
