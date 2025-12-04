from __future__ import annotations

from domain.entities.user import Doctor
from domain.repositories import IDoctorRepository, IPatientRepository, IUserRepository
from domain.services.security import PasswordHasher
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.user_exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
)


class DoctorService:
    """
    Application service for doctor-specific operations.

    Encapsulates persistence and validation while keeping orchestration
    concerns out of the web layer.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        doctor_repo: IDoctorRepository,
        patient_repo: IPatientRepository,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
    ) -> None:
        self.user_repo = user_repo
        self.doctor_repo = doctor_repo
        self.patient_repo = patient_repo
        self.uow = uow
        self.hasher = hasher

    def register_doctor(self, data: dict) -> Doctor:
        """
        Create a doctor aggregate and link patients when provided.
        """
        email = data["email"]
        if self.user_repo.get_by_email(email):
            raise UserAlreadyExistsException("Ja existeix un usuari amb aquest correu.")

        patient_emails = data.get("patients", []) or []
        patients = []
        if patient_emails:
            patients = self.patient_repo.fetch_by_emails(patient_emails)

        doctor = Doctor(
            email=email,
            password_hash=self.hasher.hash(data["password"]),
            name=data["name"],
            surname=data["surname"],
            patient_emails=list(patient_emails),
        )

        with self.uow:
            self.doctor_repo.add(doctor)
            if patients:
                # Keep bidirectional domain associations in sync
                for patient in patients:
                    if doctor.email not in patient.doctor_emails:
                        patient.doctor_emails.append(doctor.email)
                        self.patient_repo.update(patient)
            self.uow.commit()

        return doctor

    def get_doctor(self, email: str) -> Doctor:
        """
        Retrieve a doctor by email or raise if it does not exist.
        """
        doctor = self.doctor_repo.get_by_email(email)
        if doctor is None:
            raise UserNotFoundException("Metge no trobat.")
        return doctor

    def update_doctor(self, email: str, update_data: dict) -> Doctor:
        """
        Update doctor attributes and patient associations in a single transaction.
        """
        doctor = self.get_doctor(email)

        patients_list = update_data.get("patients")
        if patients_list is not None:
            normalized = patients_list or []
            # Validate referenced patients before mutating the aggregate.
            self.patient_repo.fetch_by_emails(normalized)
            update_data = {**update_data, "patients": normalized}

        doctor.set_properties(update_data, self.hasher)

        with self.uow:
            self.doctor_repo.update(doctor)
            self.uow.commit()

        return doctor

    def delete_doctor(self, email: str) -> None:
        """
        Remove a doctor and its associations.
        """
        doctor = self.get_doctor(email)

        with self.uow:
            self.doctor_repo.remove(doctor)
            self.uow.commit()
