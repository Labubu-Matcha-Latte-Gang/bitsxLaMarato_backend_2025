"""Add missing check constraints to scores table.

Revision ID: 20240912_add_checks_scores
Revises: c7f0b7f7a2b1
Create Date: 2024-09-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240912_add_checks_scores"
down_revision = "c7f0b7f7a2b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add constraints if they do not exist yet
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'non_negative_seconds_to_finish'
            ) THEN
                ALTER TABLE scores
                ADD CONSTRAINT non_negative_seconds_to_finish CHECK (seconds_to_finish >= 0);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'check_completed_at_not_future'
            ) THEN
                ALTER TABLE scores
                ADD CONSTRAINT check_completed_at_not_future CHECK (completed_at <= NOW());
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # Drop the added constraints if present
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'non_negative_seconds_to_finish'
            ) THEN
                ALTER TABLE scores DROP CONSTRAINT non_negative_seconds_to_finish;
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'check_completed_at_not_future'
            ) THEN
                ALTER TABLE scores DROP CONSTRAINT check_completed_at_not_future;
            END IF;
        END$$;
        """
    )
