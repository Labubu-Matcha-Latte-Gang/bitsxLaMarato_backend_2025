"""Drop time-based check constraints on scores and questions_answered.

Revision ID: 20240913_drop_time_checks
Revises: 20240913_update_timestamp_checks
Create Date: 2024-09-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240913_drop_time_checks"
down_revision = "20240913_update_timestamp_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE scores DROP CONSTRAINT IF EXISTS check_completed_at_not_future;
        ALTER TABLE questions_answered DROP CONSTRAINT IF EXISTS check_answered_at_not_future;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE scores
        ADD CONSTRAINT check_completed_at_not_future
            CHECK (completed_at <= statement_timestamp());
        ALTER TABLE questions_answered
        ADD CONSTRAINT check_answered_at_not_future
            CHECK (answered_at <= statement_timestamp());
        """
    )
