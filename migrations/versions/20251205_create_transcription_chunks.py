"""Create transcription_chunks table to store partial transcriptions.

Revision ID: create_transcription_chunks
Revises: cascade_delete_association_fks
Create Date: 2025-12-05 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "create_transcription_chunks"
down_revision = "cascade_delete_association_fks"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "transcription_chunks" in inspector.get_table_names():
        # Ensure the unique constraint exists even if the table was created manually.
        constraints = inspector.get_unique_constraints("transcription_chunks")
        constraint_names = {c.get("name") for c in constraints}
        if "uq_transcription_chunks_session_chunk" not in constraint_names:
            op.create_unique_constraint(
                "uq_transcription_chunks_session_chunk",
                "transcription_chunks",
                ["session_id", "chunk_index"],
            )
        indexes = {idx["name"] for idx in inspector.get_indexes("transcription_chunks")}
        if "ix_transcription_chunks_session_index" not in indexes:
            op.create_index(
                "ix_transcription_chunks_session_index",
                "transcription_chunks",
                ["session_id", "chunk_index"],
            )
        return

    op.create_table(
        "transcription_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_transcription_chunks_session_chunk",
        "transcription_chunks",
        ["session_id", "chunk_index"],
    )
    op.create_index(
        "ix_transcription_chunks_session_index",
        "transcription_chunks",
        ["session_id", "chunk_index"],
    )


def downgrade():
    op.drop_index(
        "ix_transcription_chunks_session_index",
        table_name="transcription_chunks",
    )
    op.drop_constraint(
        "uq_transcription_chunks_session_chunk",
        "transcription_chunks",
        type_="unique",
    )
    op.drop_table("transcription_chunks")
