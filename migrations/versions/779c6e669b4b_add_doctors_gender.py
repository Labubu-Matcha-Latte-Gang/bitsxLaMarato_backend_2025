"""add_doctors_gender

Revision ID: d99fd9fcba9c
Revises: ea712778b538
Create Date: 2025-12-11 17:37:36.466226
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d99fd9fcba9c"
down_revision = "ea712778b538"
branch_labels = None
depends_on = None


def upgrade():
    gender_enum = postgresql.ENUM("male", "female", "others", name="gender")
    gender_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "doctors",
        sa.Column("gender", gender_enum, nullable=True, server_default=sa.text("'male'::gender")),
    )
    op.execute("UPDATE doctors SET gender = 'male' WHERE gender IS NULL")
    op.alter_column("doctors", "gender", nullable=False, server_default=None)


def downgrade():
    op.drop_column("doctors", "gender")
