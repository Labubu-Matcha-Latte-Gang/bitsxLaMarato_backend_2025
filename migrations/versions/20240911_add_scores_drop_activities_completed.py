"""Create scores table and drop legacy activities_completed.

Revision ID: c7f0b7f7a2b1
Revises: None
Create Date: 2024-09-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c7f0b7f7a2b1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop legacy table if it exists
    op.execute("DROP TABLE IF EXISTS activities_completed CASCADE")

    op.create_table(
        "scores",
        sa.Column("patient_email", sa.String(length=120), sa.ForeignKey("patients.email", onupdate="CASCADE"), primary_key=True, nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id", onupdate="CASCADE"), primary_key=True, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), primary_key=True, nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("seconds_to_finish", sa.Float(), server_default="0", nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 10", name="check_score_range"),
        sa.CheckConstraint("seconds_to_finish >= 0", name="non_negative_seconds_to_finish"),
        sa.CheckConstraint("completed_at <= NOW()", name="check_completed_at_not_future"),
    )


def downgrade() -> None:
    op.drop_table("scores")

    # Recreate legacy table shape for backward compatibility
    op.create_table(
        "activities_completed",
        sa.Column("patient_email", sa.String(length=120), sa.ForeignKey("patients.email", onupdate="CASCADE"), primary_key=True, nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id", onupdate="CASCADE"), primary_key=True, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), primary_key=True, nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("seconds_to_finish", sa.Float(), server_default="0", nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 10", name="check_activity_completed_score_range"),
        sa.CheckConstraint("seconds_to_finish >= 0", name="non_negative_seconds_to_finish"),
    )
