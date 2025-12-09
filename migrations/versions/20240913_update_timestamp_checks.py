"""Use statement_timestamp() for time-based checks.

Revision ID: 20240913_update_timestamp_checks
Revises: 20240912_add_check_answered_at_not_future
Create Date: 2024-09-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240913_update_timestamp_checks"
down_revision = "20240912_add_check_answered_at_not_future"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recreate the time checks to rely on the statement timestamp instead of the
    # transaction start time, preventing false positives after earlier reads.
    op.execute(
        """
        ALTER TABLE scores
        DROP CONSTRAINT IF EXISTS check_completed_at_not_future,
        ADD CONSTRAINT check_completed_at_not_future
            CHECK (completed_at <= statement_timestamp());
        """
    )
    op.execute(
        """
        ALTER TABLE questions_answered
        DROP CONSTRAINT IF EXISTS check_answered_at_not_future,
        ADD CONSTRAINT check_answered_at_not_future
            CHECK (answered_at <= statement_timestamp());
        """
    )


def downgrade() -> None:
    # Restore the previous CURRENT_TIMESTAMP-based checks.
    op.execute(
        """
        ALTER TABLE scores
        DROP CONSTRAINT IF EXISTS check_completed_at_not_future,
        ADD CONSTRAINT check_completed_at_not_future
            CHECK (completed_at <= CURRENT_TIMESTAMP);
        """
    )
    op.execute(
        """
        ALTER TABLE questions_answered
        DROP CONSTRAINT IF EXISTS check_answered_at_not_future,
        ADD CONSTRAINT check_answered_at_not_future
            CHECK (answered_at <= CURRENT_TIMESTAMP);
        """
    )
