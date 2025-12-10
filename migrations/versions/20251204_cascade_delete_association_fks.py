"""Cascade delete association tables when parents are removed

Revision ID: cascade_delete_association_fks
Revises: cascade_delete_scores_on_activity
Create Date: 2025-12-04
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "cascade_delete_association_fks"
down_revision = "cascade_delete_scores_on_activity"
branch_labels = None
depends_on = None


def upgrade():
    # doctor_patient -> doctors / patients
    op.drop_constraint(
        "doctor_patient_doctor_email_fkey",
        "doctor_patient",
        type_="foreignkey",
    )
    op.drop_constraint(
        "doctor_patient_patient_email_fkey",
        "doctor_patient",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "doctor_patient_doctor_email_fkey",
        "doctor_patient",
        "doctors",
        ["doctor_email"],
        ["email"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "doctor_patient_patient_email_fkey",
        "doctor_patient",
        "patients",
        ["patient_email"],
        ["email"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )

    # user_codes -> users
    op.drop_constraint(
        "user_codes_user_email_fkey",
        "user_codes",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "user_codes_user_email_fkey",
        "user_codes",
        "users",
        ["user_email"],
        ["email"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )

    # questions_answered -> patients / questions
    op.drop_constraint(
        "questions_answered_patient_email_fkey",
        "questions_answered",
        type_="foreignkey",
    )
    op.drop_constraint(
        "questions_answered_question_id_fkey",
        "questions_answered",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "questions_answered_patient_email_fkey",
        "questions_answered",
        "patients",
        ["patient_email"],
        ["email"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "questions_answered_question_id_fkey",
        "questions_answered",
        "questions",
        ["question_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )


def downgrade():
    # doctor_patient -> doctors / patients (remove cascade delete)
    op.drop_constraint(
        "doctor_patient_doctor_email_fkey",
        "doctor_patient",
        type_="foreignkey",
    )
    op.drop_constraint(
        "doctor_patient_patient_email_fkey",
        "doctor_patient",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "doctor_patient_doctor_email_fkey",
        "doctor_patient",
        "doctors",
        ["doctor_email"],
        ["email"],
        onupdate="CASCADE",
    )
    op.create_foreign_key(
        "doctor_patient_patient_email_fkey",
        "doctor_patient",
        "patients",
        ["patient_email"],
        ["email"],
        onupdate="CASCADE",
    )

    # user_codes -> users (remove cascade delete)
    op.drop_constraint(
        "user_codes_user_email_fkey",
        "user_codes",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "user_codes_user_email_fkey",
        "user_codes",
        "users",
        ["user_email"],
        ["email"],
        onupdate="CASCADE",
    )

    # questions_answered -> patients / questions (remove cascade delete)
    op.drop_constraint(
        "questions_answered_patient_email_fkey",
        "questions_answered",
        type_="foreignkey",
    )
    op.drop_constraint(
        "questions_answered_question_id_fkey",
        "questions_answered",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "questions_answered_patient_email_fkey",
        "questions_answered",
        "patients",
        ["patient_email"],
        ["email"],
        onupdate="CASCADE",
    )
    op.create_foreign_key(
        "questions_answered_question_id_fkey",
        "questions_answered",
        "questions",
        ["question_id"],
        ["id"],
        onupdate="CASCADE",
    )
