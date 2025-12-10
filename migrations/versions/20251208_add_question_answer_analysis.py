"""Add answer text and analysis JSON to questions_answered.

Revision ID: add_question_answer_analysis
Revises: add_transcription_sessions
Create Date: 2025-12-08 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "add_question_answer_analysis"
down_revision = "add_transcription_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "questions_answered",
        sa.Column("answer_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "questions_answered",
        sa.Column(
            "analysis",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("questions_answered", "answer_text", server_default=None)
    op.alter_column("questions_answered", "analysis", server_default=None)


def downgrade():
    op.drop_column("questions_answered", "analysis")
    op.drop_column("questions_answered", "answer_text")
