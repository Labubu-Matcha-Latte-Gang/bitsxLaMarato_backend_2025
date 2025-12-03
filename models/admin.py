from __future__ import annotations

from db import db
from helpers.enums.user_role import UserRole
from models.user import User


class Admin(User):
    __tablename__ = "admins"
    __allow_unmapped__ = True

    email = db.Column(
        db.String(120),
        db.ForeignKey("users.email", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": UserRole.ADMIN,
    }
