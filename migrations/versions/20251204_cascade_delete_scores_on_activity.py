"""Cascade delete scores when removing activities

Revision ID: cascade_delete_scores_on_activity
Revises: add_role_and_patient_checks
Create Date: 2025-12-04
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "cascade_delete_scores_on_activity"
down_revision = "add_role_and_patient_checks"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("scores_activity_id_fkey", "scores", type_="foreignkey")
    op.create_foreign_key(
        "scores_activity_id_fkey",
        "scores",
        "activities",
        ["activity_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("scores_activity_id_fkey", "scores", type_="foreignkey")
    op.create_foreign_key(
        "scores_activity_id_fkey",
        "scores",
        "activities",
        ["activity_id"],
        ["id"],
        onupdate="CASCADE",
    )
