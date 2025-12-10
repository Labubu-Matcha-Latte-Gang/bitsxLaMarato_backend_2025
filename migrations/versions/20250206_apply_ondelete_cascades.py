"""Ensure FK cascades align with model definitions.

Revision ID: 20250206_apply_ondelete_cascades
Revises: 20240913_update_timestamp_checks
Create Date: 2025-02-06
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250206_apply_ondelete_cascades"
down_revision = "20240913_drop_time_checks"
branch_labels = None
depends_on = None


FK_CONSTRAINTS = [
    {
        "table": "patients",
        "name": "patients_email_fkey",
        "local_cols": ["email"],
        "remote_table": "users",
        "remote_cols": ["email"],
    },
    {
        "table": "doctors",
        "name": "doctors_email_fkey",
        "local_cols": ["email"],
        "remote_table": "users",
        "remote_cols": ["email"],
    },
    {
        "table": "admins",
        "name": "admins_email_fkey",
        "local_cols": ["email"],
        "remote_table": "users",
        "remote_cols": ["email"],
    },
    {
        "table": "doctor_patient",
        "name": "doctor_patient_doctor_email_fkey",
        "local_cols": ["doctor_email"],
        "remote_table": "doctors",
        "remote_cols": ["email"],
    },
    {
        "table": "doctor_patient",
        "name": "doctor_patient_patient_email_fkey",
        "local_cols": ["patient_email"],
        "remote_table": "patients",
        "remote_cols": ["email"],
    },
    {
        "table": "user_codes",
        "name": "user_codes_user_email_fkey",
        "local_cols": ["user_email"],
        "remote_table": "users",
        "remote_cols": ["email"],
    },
    {
        "table": "questions_answered",
        "name": "questions_answered_patient_email_fkey",
        "local_cols": ["patient_email"],
        "remote_table": "patients",
        "remote_cols": ["email"],
    },
    {
        "table": "questions_answered",
        "name": "questions_answered_question_id_fkey",
        "local_cols": ["question_id"],
        "remote_table": "questions",
        "remote_cols": ["id"],
    },
    {
        "table": "scores",
        "name": "scores_patient_email_fkey",
        "local_cols": ["patient_email"],
        "remote_table": "patients",
        "remote_cols": ["email"],
    },
    {
        "table": "scores",
        "name": "scores_activity_id_fkey",
        "local_cols": ["activity_id"],
        "remote_table": "activities",
        "remote_cols": ["id"],
    },
]


def _recreate_fk(constraint: dict, *, cascade: bool) -> None:
    """Drop and recreate a FK with the desired cascade rules."""
    on_update = "CASCADE" if cascade else "NO ACTION"
    on_delete = "CASCADE" if cascade else "NO ACTION"
    local_cols = ", ".join(constraint["local_cols"])
    remote_cols = ", ".join(constraint["remote_cols"])

    op.execute(
        f"""
        ALTER TABLE {constraint["table"]}
        DROP CONSTRAINT IF EXISTS {constraint["name"]},
        ADD CONSTRAINT {constraint["name"]}
            FOREIGN KEY ({local_cols})
            REFERENCES {constraint["remote_table"]} ({remote_cols})
            ON UPDATE {on_update} ON DELETE {on_delete};
        """
    )


def upgrade() -> None:
    # Align all FK constraints with the CASCADE semantics declared in the models.
    for constraint in FK_CONSTRAINTS:
        _recreate_fk(constraint, cascade=True)


def downgrade() -> None:
    # Restore FK constraints without cascading deletes/updates.
    for constraint in FK_CONSTRAINTS:
        _recreate_fk(constraint, cascade=False)
