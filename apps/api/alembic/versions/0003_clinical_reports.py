"""clinical_reports

Revision ID: 0003_clinical_reports
Revises: 0002_hospital
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_clinical_reports"
down_revision = "0002_hospital"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reviewed: source reports/diagnoses/symptoms, without evaluation data.
    op.create_table(
        "diagnoses",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code_system", sa.String(), nullable=True),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("diagnosed_at", sa.DateTime(), nullable=True),
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
            name=op.f("fk_diagnoses_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_diagnoses_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnoses")),
        sa.UniqueConstraint("external_id", name=op.f("uq_diagnoses_external_id")),
    )
    with op.batch_alter_table("diagnoses", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_diagnoses_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_diagnoses_patient_id"), ["patient_id"], unique=False)

    op.create_table(
        "symptoms",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("onset_at", sa.DateTime(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("frequency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
            name=op.f("fk_symptoms_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_symptoms_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_symptoms")),
        sa.UniqueConstraint("external_id", name=op.f("uq_symptoms_external_id")),
    )
    with op.batch_alter_table("symptoms", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_symptoms_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_symptoms_patient_id"), ["patient_id"], unique=False)

    op.create_table(
        "diagnostic_reports",
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("imaging_study_id", sa.Uuid(), nullable=True),
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
            name=op.f("fk_diagnostic_reports_document_id_clinical_documents"),
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id", "patient_id"],
            ["encounters.id", "encounters.patient_id"],
            name=op.f("fk_diagnostic_reports_encounter_id_encounters"),
        ),
        sa.ForeignKeyConstraint(
            ["imaging_study_id"],
            ["imaging_studies.id"],
            name=op.f("fk_diagnostic_reports_imaging_study_id_imaging_studies"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_diagnostic_reports_patient_id_patients")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnostic_reports")),
        sa.UniqueConstraint("external_id", name=op.f("uq_diagnostic_reports_external_id")),
    )
    with op.batch_alter_table("diagnostic_reports", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_diagnostic_reports_encounter_id"), ["encounter_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_diagnostic_reports_patient_id"), ["patient_id"], unique=False
        )

    op.create_table(
        "report_observations",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["lab_results.id"],
            name=op.f("fk_report_observations_observation_id_lab_results"),
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["diagnostic_reports.id"],
            name=op.f("fk_report_observations_report_id_diagnostic_reports"),
        ),
        sa.PrimaryKeyConstraint("report_id", "observation_id", name=op.f("pk_report_observations")),
    )


def downgrade() -> None:
    # Reviewed: source reports/diagnoses/symptoms, without evaluation data.
    op.drop_table("report_observations")
    with op.batch_alter_table("diagnostic_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_diagnostic_reports_patient_id"))
        batch_op.drop_index(batch_op.f("ix_diagnostic_reports_encounter_id"))

    op.drop_table("diagnostic_reports")
    with op.batch_alter_table("symptoms", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_symptoms_patient_id"))
        batch_op.drop_index(batch_op.f("ix_symptoms_encounter_id"))

    op.drop_table("symptoms")
    with op.batch_alter_table("diagnoses", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_diagnoses_patient_id"))
        batch_op.drop_index(batch_op.f("ix_diagnoses_encounter_id"))

    op.drop_table("diagnoses")
