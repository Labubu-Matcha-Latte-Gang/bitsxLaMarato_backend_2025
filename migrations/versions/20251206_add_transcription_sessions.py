"""add transcription_sessions table

Revision ID: add_transcription_sessions
Revises: cascade_delete_association_fks
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "add_transcription_sessions"       # <-- AJUSTA este ID
down_revision = "cascade_delete_association_fks"  # <-- AJUSTA según tu cadena de migraciones
branch_labels = None
depends_on = None


def upgrade():
    """Create transcription_sessions table and index on patient_email."""
    op.create_table(
        "transcription_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_email", sa.String(length=120), nullable=False),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patient_email"],
            ["patients.email"],
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_transcription_sessions_patient_email",
        "transcription_sessions",
        ["patient_email"],
    )


def downgrade():
    """Drop index and transcription_sessions table."""
    op.drop_index(
        "ix_transcription_sessions_patient_email",
        table_name="transcription_sessions",
    )
    op.drop_table("transcription_sessions")
