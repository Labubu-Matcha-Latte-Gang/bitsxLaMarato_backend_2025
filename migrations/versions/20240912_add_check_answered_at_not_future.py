"""Add not-future check to questions_answered.

Revision ID: 20240912_add_check_answered_at_not_future
Revises: 20240912_add_checks_scores
Create Date: 2024-09-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240912_add_check_answered_at_not_future"
down_revision = "20240912_add_checks_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'check_answered_at_not_future'
            ) THEN
                ALTER TABLE questions_answered
                ADD CONSTRAINT check_answered_at_not_future CHECK (answered_at <= CURRENT_TIMESTAMP);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'check_answered_at_not_future'
            ) THEN
                ALTER TABLE questions_answered
                DROP CONSTRAINT check_answered_at_not_future;
            END IF;
        END$$;
        """
    )
