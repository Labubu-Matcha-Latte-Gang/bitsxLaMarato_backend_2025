from __future__ import annotations

from datetime import timedelta
from typing import Optional

import bcrypt
from flask_jwt_extended import create_access_token

from db import db
from helpers.enums.user_role import UserRole


class User(db.Model):
    """
    Base SQLAlchemy model for users. Acts as the base table in a class-table inheritance hierarchy.
    """

    __tablename__ = "users"
    __allow_unmapped__ = True
    __table_args__ = (
        db.CheckConstraint(
            "role IS NOT NULL",
            name="ck_users_role_not_null",
        ),
    )

    email = db.Column(db.String(120), primary_key=True)
    password = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)

    __mapper_args__ = {
        "polymorphic_on": role,
    }

    def __repr__(self) -> str:
        return f"<User {self.name} {self.surname}, email {self.email}>"

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    def generate_jwt(self, expiration: Optional[timedelta] = None) -> str:
        expires = expiration or timedelta(weeks=4)
        return create_access_token(identity=self.email, expires_delta=expires)
