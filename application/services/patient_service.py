from __future__ import annotations

from domain.entities.user import Patient
from domain.repositories import IDoctorRepository, IPatientRepository, IUserRepository
from domain.services.security import PasswordHasher
from domain.strategies import IGenderParserStrategy
from domain.unit_of_work import IUnitOfWork
from helpers.enums.gender import Gender
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
        gender_parser: IGenderParserStrategy,
    ) -> None:
        self.user_repo = user_repo
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo
        self.uow = uow
        self.hasher = hasher
        self.gender_parser = gender_parser

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

        gender = self.gender_parser.parse(data["gender"])
        patient = Patient(
            email=email,
            password_hash=self.hasher.hash(data["password"]),
            name=data["name"],
            surname=data["surname"],
            ailments=data.get("ailments"),
            gender=gender,
            age=data["age"],
            treatments=data.get("treatments"),
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            doctors=doctors,
        )

        with self.uow:
            self.patient_repo.add(patient)
            if doctors:
                # Keep bidirectional domain associations in sync
                for doctor in doctors:
                    if patient.email not in doctor.patient_emails:
                        doctor.add_patients([patient])
                        self.doctor_repo.update(doctor)
            self.uow.commit()

        return patient

    def patient_exists(self, email: str) -> bool:
        """
        Check if a patient exists by email.
        """
        return self.patient_repo.get_by_email(email) is not None

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

        sanitized_updates = dict(update_data)
        doctors_list = sanitized_updates.get("doctors")
        if doctors_list is not None:
            normalized = doctors_list or []
            # Validate referenced doctors before mutating the aggregate.
            doctors = self.doctor_repo.fetch_by_emails(normalized)
            previous_doctors = {doc.email: doc for doc in patient.doctors}
            patient.replace_doctors(doctors)
            sanitized_updates = {k: v for k, v in sanitized_updates.items() if k != "doctors"}
        else:
            doctors = None

        if "gender" in sanitized_updates and sanitized_updates["gender"] is not None:
            sanitized_updates["gender"] = self.gender_parser.parse(sanitized_updates["gender"])

        patient.set_properties(sanitized_updates, self.hasher)

        with self.uow:
            if doctors is not None:
                # Remove patient from doctors no longer associated
                removed_doctors = [
                    doc for email, doc in previous_doctors.items() if email not in {d.email for d in doctors}
                ]
                for doctor in removed_doctors:
                    doctor.remove_patient(patient.email)
                    self.doctor_repo.update(doctor)

                # Add patient to newly associated doctors
                for doctor in doctors:
                    if patient.email not in doctor.patient_emails:
                        doctor.add_patients([patient])
                    self.doctor_repo.update(doctor)

            self.patient_repo.update(patient)
            self.uow.commit()

        return patient
