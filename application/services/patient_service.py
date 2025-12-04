from __future__ import annotations

from domain.entities.user import Patient
from domain.repositories import IDoctorRepository, IPatientRepository, IUserRepository
from domain.services.security import PasswordHasher
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.user_exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
)


class PatientService:
    """
    Application service for patient-specific use cases.

    Keeps user orchestration in the application layer while delegating persistence
    to repository interfaces and transaction handling to the Unit of Work.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        patient_repo: IPatientRepository,
        doctor_repo: IDoctorRepository,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
    ) -> None:
        self.user_repo = user_repo
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo
        self.uow = uow
        self.hasher = hasher

    def register_patient(self, data: dict) -> Patient:
        """
        Create a patient aggregate and link doctors when provided.
        """
        email = data["email"]
        if self.user_repo.get_by_email(email):
            raise UserAlreadyExistsException("Ja existeix un usuari amb aquest correu.")

        doctor_emails = data.get("doctors", []) or []
        doctors = []
        if doctor_emails:
            doctors = self.doctor_repo.fetch_by_emails(doctor_emails)

        patient = Patient(
            email=email,
            password_hash=self.hasher.hash(data["password"]),
            name=data["name"],
            surname=data["surname"],
            ailments=data.get("ailments"),
            gender=data["gender"],
            age=data["age"],
            treatments=data.get("treatments"),
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            doctor_emails=list(doctor_emails),
        )

        with self.uow:
            self.patient_repo.add(patient)
            if doctors:
                # Keep bidirectional domain associations in sync
                for doctor in doctors:
                    if patient.email not in doctor.patient_emails:
                        doctor.patient_emails.append(patient.email)
                        self.doctor_repo.update(doctor)
            self.uow.commit()

        return patient

    def get_patient(self, email: str) -> Patient:
        """
        Retrieve a patient by email or raise if it does not exist.
        """
        patient = self.patient_repo.get_by_email(email)
        if patient is None:
            raise UserNotFoundException("Pacient no trobat.")
        return patient

    def update_patient(self, email: str, update_data: dict) -> Patient:
        """
        Update patient attributes and doctor associations in a single transaction.
        """
        patient = self.get_patient(email)

        doctors_list = update_data.get("doctors")
        if doctors_list is not None:
            normalized = doctors_list or []
            # Validate referenced doctors before mutating the aggregate.
            self.doctor_repo.fetch_by_emails(normalized)
            update_data = {**update_data, "doctors": normalized}

        patient.set_properties(update_data, self.hasher)

        with self.uow:
            self.patient_repo.update(patient)
            self.uow.commit()

        return patient
