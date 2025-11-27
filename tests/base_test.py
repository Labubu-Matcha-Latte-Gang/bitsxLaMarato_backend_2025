from __future__ import annotations

from abc import ABC
from typing import Any
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from helpers.enums.gender import Gender
from models.admin import Admin
from models.doctor import Doctor
from models.patient import Patient
from models.user import User


class BaseTest(ABC):
    """
    Base helper class for API integration tests.
    Injects Flask app, client y sesión de DB vía fixture autouse.
    """

    default_password = "Password1"

    @pytest.fixture(autouse=True)
    def _inject_dependencies(self, app, client, db_session):
        self.app = app
        self.client = client
        self.db = db_session
        self.api_prefix: str = app.config["API_PREFIX"]
        self.version_endpoint: str = app.config["VERSION_ENDPOINT"]
        yield

    @staticmethod
    def unique_email(prefix: str = "user") -> str:
        return f"{prefix}_{uuid4().hex}@example.com"

    def auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def make_patient_payload(self, **overrides: Any) -> dict[str, Any]:
        email = overrides.get("email") or self.unique_email("patient")
        payload = {
            "email": email,
            "password": overrides.get("password", self.default_password),
            "name": overrides.get("name", "John"),
            "surname": overrides.get("surname", "Doe"),
            "gender": overrides.get("gender", Gender.MALE.value),
            "age": overrides.get("age", 30),
            "height_cm": overrides.get("height_cm", 180.0),
            "weight_kg": overrides.get("weight_kg", 75.0),
            "ailments": overrides.get("ailments"),
            "treatments": overrides.get("treatments"),
            "doctors": overrides.get("doctors", []),
        }
        return payload

    def make_doctor_payload(self, **overrides: Any) -> dict[str, Any]:
        email = overrides.get("email") or self.unique_email("doctor")
        payload = {
            "email": email,
            "password": overrides.get("password", self.default_password),
            "name": overrides.get("name", "Doc"),
            "surname": overrides.get("surname", "Tor"),
            "patients": overrides.get("patients", []),
        }
        return payload

    def register_patient(self, payload: dict[str, Any] | None = None):
        payload = payload or self.make_patient_payload()
        return self.client.post(f"{self.api_prefix}/user/patient", json=payload)

    def register_doctor(self, payload: dict[str, Any] | None = None):
        payload = payload or self.make_doctor_payload()
        return self.client.post(f"{self.api_prefix}/user/doctor", json=payload)

    def login(self, email: str, password: str):
        return self.client.post(
            f"{self.api_prefix}/user/login", json={"email": email, "password": password}
        )

    def login_and_get_token(self, email: str, password: str) -> str:
        response = self.login(email, password)
        body = response.get_json() or {}
        return body.get("access_token", "")

    def create_admin(self, email: str | None = None, password: str | None = None) -> User:
        email = email or self.unique_email("admin")
        password = password or self.default_password
        user = User(
            email=email,
            password=User.hash_password(password),
            name="Admin",
            surname="User",
        )
        admin = Admin(email=email, user=user)
        self.db.add(user)
        self.db.add(admin)
        self.db.commit()
        return user

    def create_patient_model(
        self,
        email: str | None = None,
        password: str | None = None,
        name: str = "John",
        surname: str = "Doe",
    ) -> User:
        email = email or self.unique_email("patient")
        password = password or self.default_password
        user = User(
            email=email,
            password=User.hash_password(password),
            name=name,
            surname=surname,
        )
        patient = Patient(
            email=email,
            ailments=None,
            gender=Gender.MALE,
            age=30,
            treatments=None,
            height_cm=180.0,
            weight_kg=75.0,
            user=user,
        )
        self.db.add(user)
        self.db.add(patient)
        self.db.commit()
        return user

    def create_doctor_model(
        self,
        email: str | None = None,
        password: str | None = None,
        name: str = "Doc",
        surname: str = "Tor",
    ) -> User:
        email = email or self.unique_email("doctor")
        password = password or self.default_password
        user = User(
            email=email,
            password=User.hash_password(password),
            name=name,
            surname=surname,
        )
        doctor = Doctor(email=email, user=user)
        self.db.add(user)
        self.db.add(doctor)
        self.db.commit()
        return user

    def generate_token(self, email: str) -> str:
        with self.app.app_context():
            return create_access_token(identity=email)
