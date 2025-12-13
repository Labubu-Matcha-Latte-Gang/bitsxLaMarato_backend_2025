"""add_question_answered_primary_key

Revision ID: eeb7844648fe
Revises: bdc3462def1e
Create Date: 2025-12-13 17:22:50.658461
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "eeb7844648fe"
down_revision = "bdc3462def1e"
branch_labels = None
depends_on = None


def upgrade():
    # Drop old PK (patient_email, question_id)
    op.drop_constraint(
        "questions_answered_pkey",
        "questions_answered",
        type_="primary",
    )

    # Create new PK (patient_email, question_id, answered_at)
    op.create_primary_key(
        "questions_answered_pkey",
        "questions_answered",
        ["patient_email", "question_id", "answered_at"],
    )


def downgrade():
    # Drop new PK (patient_email, question_id, answered_at)
    op.drop_constraint(
        "questions_answered_pkey",
        "questions_answered",
        type_="primary",
    )

    # Restore old PK (patient_email, question_id)
    op.create_primary_key(
        "questions_answered_pkey",
        "questions_answered",
        ["patient_email", "question_id"],
    )
