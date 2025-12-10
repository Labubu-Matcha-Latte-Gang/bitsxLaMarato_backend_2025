"""Add role to users and patient numeric checks

Revision ID: add_role_and_patient_checks
Revises: 
Create Date: 2025-12-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_role_and_patient_checks"
down_revision = "20250206_apply_ondelete_cascades"
branch_labels = None
depends_on = None


def upgrade():
    # Use existing enum type name to avoid creating a duplicate
    userrole_enum = postgresql.ENUM("patient", "doctor", "admin", name="userrole")

    op.add_column(
        "users",
        sa.Column("role", userrole_enum, nullable=True),
    )

    # Populate roles based on existing role tables
    op.execute(
        """
        UPDATE users SET role = 'patient'
        WHERE role IS NULL AND EXISTS (SELECT 1 FROM patients p WHERE p.email = users.email);
        """
    )
    op.execute(
        """
        UPDATE users SET role = 'doctor'
        WHERE EXISTS (SELECT 1 FROM doctors d WHERE d.email = users.email);
        """
    )
    op.execute(
        """
        UPDATE users SET role = 'admin'
        WHERE EXISTS (SELECT 1 FROM admins a WHERE a.email = users.email);
        """
    )

    op.alter_column("users", "role", nullable=False)

    # Patient numeric checks
    op.create_check_constraint(
        "ck_patient_age_range", "patients", "age >= 0 AND age <= 120"
    )
    op.create_check_constraint(
        "ck_patient_height_range",
        "patients",
        "height_cm > 0 AND height_cm <= 250",
    )
    op.create_check_constraint(
        "ck_patient_weight_range",
        "patients",
        "weight_kg > 0 AND weight_kg <= 600",
    )


def downgrade():
    # Drop constraints
    op.drop_constraint("ck_patient_weight_range", "patients", type_="check")
    op.drop_constraint("ck_patient_height_range", "patients", type_="check")
    op.drop_constraint("ck_patient_age_range", "patients", type_="check")

    # Drop role column (keep enum type intact if shared)
    op.drop_column("users", "role")
