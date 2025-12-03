from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped

from db import db
from helpers.enums.user_role import UserRole
from models.associations import DoctorPatientAssociation
from models.user import User

if TYPE_CHECKING:
    from models.patient import Patient


class Doctor(User):
    __tablename__ = "doctors"
    __allow_unmapped__ = True

    email = db.Column(
        db.String(120),
        db.ForeignKey("users.email", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    patients: Mapped[list["Patient"]] = db.relationship(
        "Patient",
        secondary=DoctorPatientAssociation.__table__,
        back_populates="doctors",
        lazy=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": UserRole.DOCTOR,
    }
