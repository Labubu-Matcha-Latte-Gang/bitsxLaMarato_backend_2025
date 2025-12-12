"""add_diary_enum

Revision ID: bdc3462def1e
Revises: d99fd9fcba9c
Create Date: 2025-12-12 21:15:33.486244
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bdc3462def1e'
down_revision = 'd99fd9fcba9c'
branch_labels = None
depends_on = None


def upgrade():
    # Añade el valor 'diary' al enum de question_type
    op.execute("ALTER TYPE questiontype ADD VALUE 'DIARY'")


def downgrade():
    # PostgreSQL no permite eliminar valores de enum directamente,
    # por lo que se recrea el tipo sin 'diary'
    op.execute("ALTER TYPE questiontype RENAME TO questiontype_old")
    op.create_enum('questiontype', ['CONCENTRATION', 'SPEED', 'WORDS', 'SORTING', 'MULTITASKING'])
    op.alter_column('questions', 'question_type', type_=sa.Enum('CONCENTRATION', 'SPEED', 'WORDS', 'SORTING', 'MULTITASKING', name='questiontype'), existing_type=sa.Enum('CONCENTRATION', 'SPEED', 'WORDS', 'SORTING', 'MULTITASKING', 'DIARY', name='questiontype_old'))
    op.alter_column('activities', 'activity_type', type_=sa.Enum('CONCENTRATION', 'SPEED', 'WORDS', 'SORTING', 'MULTITASKING', name='questiontype'), existing_type=sa.Enum('CONCENTRATION', 'SPEED', 'WORDS', 'SORTING', 'MULTITASKING', 'DIARY', name='questiontype_old'))
    op.execute("DROP TYPE questiontype_old")
