"""hospital_foundation

Revision ID: 0002_hospital
Revises: 0001_foundation
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_hospital"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reviewed: clinical metadata only; evaluation data has no tables.
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("synthetic_label", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
        sa.UniqueConstraint("external_id", name=op.f("uq_assets_external_id")),
    )
    op.create_table(
        "case_datasets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("dataset_version", sa.String(), nullable=False),
        sa.Column("seed_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("seeded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_datasets")),
        sa.UniqueConstraint("case_id", "dataset_version", name=op.f("uq_case_datasets_case_id")),
    )
    op.create_table(
        "patients",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("synthetic_mrn", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.CheckConstraint("is_synthetic = 1", name=op.f("ck_patients_synthetic_only")),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["case_datasets.id"], name=op.f("fk_patients_dataset_id_case_datasets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
        sa.UniqueConstraint("dataset_id", "synthetic_mrn", name=op.f("uq_patients_dataset_id")),
        sa.UniqueConstraint("external_id", name=op.f("uq_patients_external_id")),
    )
    op.create_table(
        "encounters",
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("department", sa.String(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("facility_label", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name=op.f("ck_encounters_chronology")
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_encounters_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_encounters")),
        sa.UniqueConstraint("external_id", name=op.f("uq_encounters_external_id")),
        sa.UniqueConstraint("id", "patient_id", name=op.f("uq_encounters_id")),
    )
    with op.batch_alter_table("encounters", schema=None) as batch_op:
        batch_op.create_index(
            "ix_encounters_patient_time", ["patient_id", "started_at", "external_id"], unique=False
        )

    op.create_table(
        "clinical_documents",
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("author_label", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("event_at", sa.DateTime(), nullable=True),
        sa.Column("authored_at", sa.DateTime(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_clinical_documents_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_clinical_documents_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_documents")),
        sa.UniqueConstraint("external_id", name=op.f("uq_clinical_documents_external_id")),
        sa.UniqueConstraint("id", "patient_id", name=op.f("uq_clinical_documents_id")),
    )
    with op.batch_alter_table("clinical_documents", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_clinical_documents_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_clinical_documents_patient_id"), ["patient_id"], unique=False
        )

    op.create_table(
        "lab_orders",
        sa.Column("ordered_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("panel_code", sa.String(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_lab_orders_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_lab_orders_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lab_orders")),
        sa.UniqueConstraint("external_id", name=op.f("uq_lab_orders_external_id")),
        sa.UniqueConstraint("id", "patient_id", name=op.f("uq_lab_orders_id")),
    )
    with op.batch_alter_table("lab_orders", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_lab_orders_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_lab_orders_patient_id"), ["patient_id"], unique=False)

    op.create_table(
        "clinical_events",
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_time", sa.DateTime(), nullable=True),
        sa.Column("time_precision", sa.String(), nullable=False),
        sa.Column("time_raw", sa.String(), nullable=True),
        sa.Column("documented_at", sa.DateTime(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_clinical_events_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_clinical_events_patient_id_patients")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id", "patient_id"],
            ["clinical_documents.id", "clinical_documents.patient_id"],
            name=op.f("fk_clinical_events_source_document_id_clinical_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_events")),
        sa.UniqueConstraint("external_id", name=op.f("uq_clinical_events_external_id")),
    )
    with op.batch_alter_table("clinical_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_clinical_events_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_clinical_events_patient_id"), ["patient_id"], unique=False
        )

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("amended_at", sa.DateTime(), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["assets.id"], name=op.f("fk_document_versions_artifact_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["clinical_documents.id"],
            name=op.f("fk_document_versions_document_id_clinical_documents"),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_versions_supersedes_version_id_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
        sa.UniqueConstraint(
            "document_id", "version_number", name=op.f("uq_document_versions_document_id")
        ),
    )
    op.create_table(
        "imaging_studies",
        sa.Column("modality", sa.String(), nullable=False),
        sa.Column("body_region", sa.String(), nullable=False),
        sa.Column("ordered_at", sa.DateTime(), nullable=True),
        sa.Column("performed_at", sa.DateTime(), nullable=True),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
        sa.Column("report_document_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_imaging_studies_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_imaging_studies_patient_id_patients")
        ),
        sa.ForeignKeyConstraint(
            ["report_document_id"],
            ["clinical_documents.id"],
            name=op.f("fk_imaging_studies_report_document_id_clinical_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imaging_studies")),
        sa.UniqueConstraint("external_id", name=op.f("uq_imaging_studies_external_id")),
    )
    with op.batch_alter_table("imaging_studies", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_imaging_studies_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_imaging_studies_patient_id"), ["patient_id"], unique=False
        )

    op.create_table(
        "lab_results",
        sa.Column("lab_order_id", sa.Uuid(), nullable=True),
        sa.Column("analyte_code", sa.String(), nullable=True),
        sa.Column("test_name", sa.String(), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("reference_low", sa.Float(), nullable=True),
        sa.Column("reference_high", sa.Float(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=True),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_lab_results_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["lab_order_id"], ["lab_orders.id"], name=op.f("fk_lab_results_lab_order_id_lab_orders")
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_lab_results_patient_id_patients")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id", "patient_id"],
            ["clinical_documents.id", "clinical_documents.patient_id"],
            name=op.f("fk_lab_results_source_document_id_clinical_documents"),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["lab_results.id"],
            name=op.f("fk_lab_results_supersedes_id_lab_results"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lab_results")),
        sa.UniqueConstraint("external_id", name=op.f("uq_lab_results_external_id")),
    )
    with op.batch_alter_table("lab_results", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_lab_results_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_lab_results_patient_id"), ["patient_id"], unique=False)

    op.create_table(
        "medication_events",
        sa.Column("record_type", sa.String(), nullable=False),
        sa.Column("drug_name", sa.String(), nullable=False),
        sa.Column("generic_name", sa.String(), nullable=True),
        sa.Column("dose", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("route", sa.String(), nullable=True),
        sa.Column("frequency", sa.String(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(), nullable=True),
        sa.Column("effective_at", sa.DateTime(), nullable=True),
        sa.Column("administered_at", sa.DateTime(), nullable=True),
        sa.Column("discontinued_at", sa.DateTime(), nullable=True),
        sa.Column("prescriber", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("parent_event_id", sa.Uuid(), nullable=True),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_medication_events_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_event_id"],
            ["medication_events.id"],
            name=op.f("fk_medication_events_parent_event_id_medication_events"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_medication_events_patient_id_patients")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id", "patient_id"],
            ["clinical_documents.id", "clinical_documents.patient_id"],
            name=op.f("fk_medication_events_source_document_id_clinical_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medication_events")),
        sa.UniqueConstraint("external_id", name=op.f("uq_medication_events_external_id")),
    )
    with op.batch_alter_table("medication_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_medication_events_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_medication_events_patient_id"), ["patient_id"], unique=False
        )

    op.create_table(
        "referrals",
        sa.Column("origin_service", sa.String(), nullable=False),
        sa.Column("destination_service", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["clinical_documents.id"],
            name=op.f("fk_referrals_document_id_clinical_documents"),
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_referrals_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_referrals_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referrals")),
        sa.UniqueConstraint("external_id", name=op.f("uq_referrals_external_id")),
    )
    with op.batch_alter_table("referrals", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_referrals_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_referrals_patient_id"), ["patient_id"], unique=False)

    op.create_table(
        "imaging_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("study_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("series_label", sa.String(), nullable=True),
        sa.Column("asset_kind", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_imaging_assets_asset_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["study_id"],
            ["imaging_studies.id"],
            name=op.f("fk_imaging_assets_study_id_imaging_studies"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imaging_assets")),
        sa.UniqueConstraint("external_id", name=op.f("uq_imaging_assets_external_id")),
        sa.UniqueConstraint("study_id", "asset_id", name=op.f("uq_imaging_assets_study_id")),
    )


def downgrade() -> None:
    # Reviewed: clinical metadata only; evaluation data has no tables.
    op.drop_table("imaging_assets")
    with op.batch_alter_table("referrals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_referrals_patient_id"))
        batch_op.drop_index(batch_op.f("ix_referrals_encounter_id"))

    op.drop_table("referrals")
    with op.batch_alter_table("medication_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_medication_events_patient_id"))
        batch_op.drop_index(batch_op.f("ix_medication_events_encounter_id"))

    op.drop_table("medication_events")
    with op.batch_alter_table("lab_results", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_lab_results_patient_id"))
        batch_op.drop_index(batch_op.f("ix_lab_results_encounter_id"))

    op.drop_table("lab_results")
    with op.batch_alter_table("imaging_studies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_imaging_studies_patient_id"))
        batch_op.drop_index(batch_op.f("ix_imaging_studies_encounter_id"))

    op.drop_table("imaging_studies")
    op.drop_table("document_versions")
    with op.batch_alter_table("clinical_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_clinical_events_patient_id"))
        batch_op.drop_index(batch_op.f("ix_clinical_events_encounter_id"))

    op.drop_table("clinical_events")
    with op.batch_alter_table("lab_orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_lab_orders_patient_id"))
        batch_op.drop_index(batch_op.f("ix_lab_orders_encounter_id"))

    op.drop_table("lab_orders")
    with op.batch_alter_table("clinical_documents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_clinical_documents_patient_id"))
        batch_op.drop_index(batch_op.f("ix_clinical_documents_encounter_id"))

    op.drop_table("clinical_documents")
    with op.batch_alter_table("encounters", schema=None) as batch_op:
        batch_op.drop_index("ix_encounters_patient_time")

    op.drop_table("encounters")
    op.drop_table("patients")
    op.drop_table("case_datasets")
    op.drop_table("assets")
