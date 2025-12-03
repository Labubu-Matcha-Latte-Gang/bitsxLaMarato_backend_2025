from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from helpers.enums.gender import Gender
from helpers.enums.user_role import UserRole
from domain.services.security import PasswordHasher


@dataclass
class User(ABC):
    """
    Domain abstraction for a user. Acts as the aggregate root for role-specific subclasses.
    """

    email: str
    password_hash: str
    name: str
    surname: str

    @property
    @abstractmethod
    def role(self) -> UserRole:
        raise NotImplementedError()

    @abstractmethod
    def role_payload(self) -> dict:
        """
        Return role-specific data for serialization.
        """
        raise NotImplementedError()

    @abstractmethod
    def doctor_of_this_patient(self, patient: "Patient") -> bool:
        """
        Authorization hook used to check if this user can access a patient.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_role_associations(self) -> None:
        """
        Clear associations between roles (e.g., doctor-patient links).
        """
        raise NotImplementedError()

    def to_dict(self) -> dict:
        """
        Public representation combining base fields and role payload.
        """
        payload = {
            "email": self.email,
            "name": self.name,
            "surname": self.surname,
        }
        payload["role"] = self.role_payload()
        return payload

    def check_password(self, password: str, hasher: PasswordHasher) -> bool:
        return hasher.verify(password, self.password_hash)

    def set_password(self, new_password: str, hasher: PasswordHasher) -> None:
        self.password_hash = hasher.hash(new_password)

    def set_properties(self, data: dict, hasher: PasswordHasher) -> None:
        if "email" in data:
            self.email = data["email"]
        if "name" in data:
            self.name = data["name"]
        if "surname" in data:
            self.surname = data["surname"]
        if "password" in data:
            self.set_password(data["password"], hasher)


@dataclass
class Patient(User):
    ailments: Optional[str]
    gender: Gender
    age: int
    treatments: Optional[str]
    height_cm: float
    weight_kg: float
    doctor_emails: List[str] = field(default_factory=list)

    @property
    def role(self) -> UserRole:
        return UserRole.PATIENT

    def add_doctors(self, doctors: List[str]) -> None:
        for doctor_email in doctors:
            if doctor_email and doctor_email not in self.doctor_emails:
                self.doctor_emails.append(doctor_email)

    def replace_doctors(self, doctors: List[str]) -> None:
        self.doctor_emails = [email for email in doctors if email]

    def role_payload(self) -> dict:
        return {
            "ailments": self.ailments,
            "gender": self.gender.value if self.gender else None,
            "age": self.age,
            "treatments": self.treatments,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "doctors": list(self.doctor_emails),
        }

    def doctor_of_this_patient(self, patient: "Patient") -> bool:
        # Patients cannot access other patients.
        return False

    def remove_role_associations(self) -> None:
        self.doctor_emails.clear()

    def get_daily_question_filters(self) -> dict:
        return {}

    def get_recommended_activity_filters(self) -> dict:
        return {}

    def set_properties(self, data: dict, hasher: PasswordHasher) -> None:
        super().set_properties(data, hasher)
        if "ailments" in data:
            self.ailments = data["ailments"]
        if "gender" in data and data["gender"] is not None:
            self.gender = data["gender"]
        if "age" in data and data["age"] is not None:
            self.age = data["age"]
        if "treatments" in data:
            self.treatments = data["treatments"]
        if "height_cm" in data and data["height_cm"] is not None:
            self.height_cm = data["height_cm"]
        if "weight_kg" in data and data["weight_kg"] is not None:
            self.weight_kg = data["weight_kg"]
        if "doctors" in data and data["doctors"] is not None:
            self.replace_doctors(data["doctors"])


@dataclass
class Doctor(User):
    patient_emails: List[str] = field(default_factory=list)

    @property
    def role(self) -> UserRole:
        return UserRole.DOCTOR

    def add_patients(self, patients: List[str]) -> None:
        for patient_email in patients:
            if patient_email and patient_email not in self.patient_emails:
                self.patient_emails.append(patient_email)

    def replace_patients(self, patients: List[str]) -> None:
        self.patient_emails = [email for email in patients if email]

    def role_payload(self) -> dict:
        return {
            "patients": list(self.patient_emails),
        }

    def doctor_of_this_patient(self, patient: Patient) -> bool:
        return patient.email in self.patient_emails

    def remove_role_associations(self) -> None:
        self.patient_emails.clear()

    def set_properties(self, data: dict, hasher: PasswordHasher) -> None:
        super().set_properties(data, hasher)
        if "patients" in data and data["patients"] is not None:
            self.replace_patients(data["patients"])


@dataclass
class Admin(User):
    @property
    def role(self) -> UserRole:
        return UserRole.ADMIN

    def role_payload(self) -> dict:
        return {}

    def doctor_of_this_patient(self, patient: Patient) -> bool:
        return True

    def remove_role_associations(self) -> None:
        # Admin currently has no associations.
        return
