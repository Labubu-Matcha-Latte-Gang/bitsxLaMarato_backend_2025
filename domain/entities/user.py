from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from helpers.enums.gender import Gender
from helpers.enums.user_role import UserRole
from domain.services.security import PasswordHasher

if TYPE_CHECKING:
    from domain.services.recommendation import DailyQuestionFilterStrategy
    from domain.repositories.interfaces import IScoreRepository, ITranscriptionAnalysisRepository
    from domain.services.recommendation import ScoreBasedQuestionStrategy

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
    doctors: List["Doctor"] = field(default_factory=list)

    @property
    def role(self) -> UserRole:
        return UserRole.PATIENT

    def role_payload(self) -> dict:
        return {
            "ailments": self.ailments,
            "gender": self.gender.value if self.gender else None,
            "age": self.age,
            "treatments": self.treatments,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "doctors": [doctor.email for doctor in self.doctors],
        }

    def doctor_of_this_patient(self, patient: "Patient") -> bool:
        return False

    def remove_role_associations(self) -> None:
        self.doctors.clear()

    def get_daily_question_filters(
        self,
        score_repo: IScoreRepository,
        transcription_repo: ITranscriptionAnalysisRepository,
        strategy: DailyQuestionFilterStrategy | None = None,
    ) -> dict:
        """
        Generate filters for selecting the patient's daily question using an
        injectable strategy.
        """

        if strategy is None:
            strategy = ScoreBasedQuestionStrategy()

        return strategy.get_filters(self, score_repo, transcription_repo)

    def get_recommended_activity_filters(self) -> dict:
        """
        Generate filters for recommended activity selection based on patient attributes.
        Returns:
            dict: Filters to apply when selecting recommended activities.
        """
        return {} #TODO: Implement based on patient attributes

    @property
    def doctor_emails(self) -> List[str]:
        return [doctor.email for doctor in self.doctors]

    def add_doctors(self, doctors: List["Doctor"]) -> None:
        existing = {doctor.email for doctor in self.doctors}
        for doctor in doctors:
            if doctor and doctor.email not in existing:
                self.doctors.append(doctor)
                existing.add(doctor.email)

    def replace_doctors(self, doctors: List["Doctor"]) -> None:
        unique = {}
        for doctor in doctors:
            if doctor and doctor.email not in unique:
                unique[doctor.email] = doctor
        self.doctors = list(unique.values())

    def remove_doctor(self, doctor_email: str) -> None:
        self.doctors = [doctor for doctor in self.doctors if doctor.email != doctor_email]

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


@dataclass
class Doctor(User):
    patients: List[Patient] = field(default_factory=list)

    @property
    def role(self) -> UserRole:
        return UserRole.DOCTOR

    def role_payload(self) -> dict:
        return {
            "patients": [patient.email for patient in self.patients],
        }

    def doctor_of_this_patient(self, patient: Patient) -> bool:
        return any(patient.email == p.email for p in self.patients)

    def remove_role_associations(self) -> None:
        self.patients.clear()

    def set_properties(self, data: dict, hasher: PasswordHasher) -> None:
        super().set_properties(data, hasher)

    @property
    def patient_emails(self) -> List[str]:
        return [patient.email for patient in self.patients]

    def add_patients(self, patients: List[Patient]) -> None:
        existing = {patient.email for patient in self.patients}
        for patient in patients:
            if patient and patient.email not in existing:
                self.patients.append(patient)
                existing.add(patient.email)

    def replace_patients(self, patients: List[Patient]) -> None:
        unique = {}
        for patient in patients:
            if patient and patient.email not in unique:
                unique[patient.email] = patient
        self.patients = list(unique.values())

    def remove_patient(self, patient_email: str) -> None:
        self.patients = [patient for patient in self.patients if patient.email != patient_email]


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
