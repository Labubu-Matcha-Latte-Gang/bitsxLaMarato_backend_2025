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
        """
        Role discriminator for the concrete user type.

        Returns:
            UserRole: Enum value identifying the concrete role.

        Raises:
            NotImplementedError: When a subclass does not implement the property.
        """
        raise NotImplementedError()

    @abstractmethod
    def role_payload(self) -> dict:
        """
        Return role-specific data for serialization.

        Returns:
            dict: Role-specific fields to include in public representations.

        Raises:
            NotImplementedError: When a subclass does not implement the method.
        """
        raise NotImplementedError()

    @abstractmethod
    def doctor_of_this_patient(self, patient: "Patient") -> bool:
        """
        Authorization hook used to check if this user can access a patient.

        Args:
            patient (Patient): Patient to evaluate access against.

        Returns:
            bool: True if this user is allowed to access the given patient.

        Raises:
            NotImplementedError: When a subclass does not implement the method.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_role_associations(self) -> None:
        """
        Clear associations between roles (e.g., doctor-patient links).

        Raises:
            NotImplementedError: When a subclass does not implement the method.
        """
        raise NotImplementedError()

    def to_dict(self) -> dict:
        """
        Public representation combining base fields and role payload.

        Returns:
            dict: Serializable structure with base user data and role payload.
        """
        payload = {
            "email": self.email,
            "name": self.name,
            "surname": self.surname,
        }
        payload["role"] = self.role_payload()
        return payload

    def check_password(self, password: str, hasher: PasswordHasher) -> bool:
        """
        Verify a plaintext password with the provided hasher.

        Args:
            password (str): Plaintext password to verify.
            hasher (PasswordHasher): Hashing service to use.

        Returns:
            bool: True if the password matches the stored hash.
        """
        return hasher.verify(password, self.password_hash)

    def set_password(self, new_password: str, hasher: PasswordHasher) -> None:
        """
        Replace the current password hash with a hash of the provided password.

        Args:
            new_password (str): New plaintext password.
            hasher (PasswordHasher): Hashing service to use.
        """
        self.password_hash = hasher.hash(new_password)

    def set_properties(self, data: dict, hasher: PasswordHasher) -> None:
        """
        Update mutable base fields from a payload.

        Args:
            data (dict): Fields to update (email, name, surname, password).
            hasher (PasswordHasher): Hashing service for password changes.
        """
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
        """
        Add doctor emails to the association list, avoiding duplicates and blanks.

        Args:
            doctors (List[str]): Doctor emails to add.
        """
        for doctor_email in doctors:
            if doctor_email and doctor_email not in self.doctor_emails:
                self.doctor_emails.append(doctor_email)

    def replace_doctors(self, doctors: List[str]) -> None:
        """
        Replace doctor associations with the provided list.

        Args:
            doctors (List[str]): Doctor emails to set.
        """
        self.doctor_emails = [email for email in doctors if email]

    def role_payload(self) -> dict:
        """
        Payload with patient-specific fields for serialization.

        Returns:
            dict: Patient data including demographics and linked doctors.
        """
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
        """
        Patients cannot access other patients.

        Args:
            patient (Patient): Patient being accessed.

        Returns:
            bool: Always False for Patient role.
        """
        return False

    def remove_role_associations(self) -> None:
        """
        Clear doctor associations for the patient.
        """
        self.doctor_emails.clear()

    def get_daily_question_filters(self) -> dict:
        """
        Compute filters to select a daily question for this patient.

        Returns:
            dict: Filter arguments for the question repository.
        """
        return {}

    def get_recommended_activity_filters(self) -> dict:
        """
        Compute filters to select a recommended activity for this patient.

        Returns:
            dict: Filter arguments for the activity repository.
        """
        return {}

    def set_properties(self, data: dict, hasher: PasswordHasher) -> None:
        """
        Update patient-specific and base fields from a payload.

        Args:
            data (dict): Fields to update.
            hasher (PasswordHasher): Hashing service for password changes.
        """
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
        """
        Add patient associations, skipping blanks and duplicates.

        Args:
            patients (List[str]): Patient emails to add.
        """
        for patient_email in patients:
            if patient_email and patient_email not in self.patient_emails:
                self.patient_emails.append(patient_email)

    def replace_patients(self, patients: List[str]) -> None:
        """
        Replace the current patient associations.

        Args:
            patients (List[str]): Patient emails to set.
        """
        self.patient_emails = [email for email in patients if email]

    def role_payload(self) -> dict:
        """
        Payload with doctor-specific fields for serialization.

        Returns:
            dict: Patients linked to this doctor.
        """
        return {
            "patients": list(self.patient_emails),
        }

    def doctor_of_this_patient(self, patient: Patient) -> bool:
        """
        Determine if this doctor is linked to the given patient.

        Args:
            patient (Patient): Patient being accessed.

        Returns:
            bool: True if patient email is in doctor's list.
        """
        return patient.email in self.patient_emails

    def remove_role_associations(self) -> None:
        """
        Clear patient associations for the doctor.
        """
        self.patient_emails.clear()

    def set_properties(self, data: dict, hasher: PasswordHasher) -> None:
        """
        Update doctor-specific and base fields from a payload.

        Args:
            data (dict): Fields to update.
            hasher (PasswordHasher): Hashing service for password changes.
        """
        super().set_properties(data, hasher)
        if "patients" in data and data["patients"] is not None:
            self.replace_patients(data["patients"])


@dataclass
class Admin(User):
    @property
    def role(self) -> UserRole:
        return UserRole.ADMIN

    def role_payload(self) -> dict:
        """
        Payload for admin role (empty as of now).

        Returns:
            dict: Empty payload for admin users.
        """
        return {}

    def doctor_of_this_patient(self, patient: Patient) -> bool:
        """
        Admins can access any patient.

        Args:
            patient (Patient): Patient being accessed.

        Returns:
            bool: Always True for Admin role.
        """
        return True

    def remove_role_associations(self) -> None:
        # Admin currently has no associations.
        return
