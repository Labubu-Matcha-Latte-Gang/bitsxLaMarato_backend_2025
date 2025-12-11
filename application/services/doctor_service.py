from __future__ import annotations

from domain.entities.user import Doctor, Patient
from domain.repositories import IDoctorRepository, IPatientRepository, IUserRepository
from domain.services.security import PasswordHasher
from domain.unit_of_work import IUnitOfWork
from helpers.enums.gender import Gender
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

        gender = self._parse_gender(data["gender"])
        doctor = Doctor(
            email=email,
            password_hash=self.hasher.hash(data["password"]),
            name=data["name"],
            surname=data["surname"],
            gender=gender,
            patients=patients,
        )

        with self.uow:
            self.doctor_repo.add(doctor)
            if patients:
                # Keep bidirectional domain associations in sync
                for patient in patients:
                    if doctor.email not in patient.doctor_emails:
                        patient.add_doctors([doctor])
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

        sanitized_updates = dict(update_data)
        patients_list = sanitized_updates.get("patients")
        previous_patients = {}
        if patients_list is not None:
            normalized = patients_list or []
            # Validate referenced patients before mutating the aggregate.
            patients = self.patient_repo.fetch_by_emails(normalized)
            previous_patients = {p.email: p for p in doctor.patients}
            doctor.replace_patients(patients)
            sanitized_updates = {k: v for k, v in sanitized_updates.items() if k != "patients"}
        else:
            patients = None

        if "gender" in sanitized_updates and sanitized_updates["gender"] is not None:
            sanitized_updates["gender"] = self._parse_gender(sanitized_updates["gender"])

        doctor.set_properties(sanitized_updates, self.hasher)

        with self.uow:
            if patients is not None:
                removed_patients = [
                    p for email_key, p in previous_patients.items() if email_key not in {p.email for p in patients}
                ]
                for patient in removed_patients:
                    patient.remove_doctor(doctor.email)
                    self.patient_repo.update(patient)

                for patient in patients:
                    if doctor.email not in patient.doctor_emails:
                        patient.add_doctors([doctor])
                    self.patient_repo.update(patient)

            self.doctor_repo.update(doctor)
            self.uow.commit()

        return doctor

    def search_patients(self, doctor_email: str, query: str, limit: int = 20) -> list[Patient]:
        """
        Allow a doctor to search any patient by partial name or surname.
        """
        # Still validate the doctor exists before running the search
        self.get_doctor(doctor_email)
        return self.patient_repo.search_by_name(query, limit=limit)

    def delete_doctor(self, email: str) -> None:
        """
        Remove a doctor and its associations.
        """
        doctor = self.get_doctor(email)

        with self.uow:
            self.doctor_repo.remove(doctor)
            self.uow.commit()

    def add_patients(self, doctor_email: str, patient_emails: list[str]) -> Doctor:
        """
        Associa múltiples pacients a un doctor, mantenint els enllaços bidireccionals.

        Si la llista d'emails de pacients és buida o no conté cap email vàlid, es llança una excepció amb un missatge en català.
        """
        doctor = self.get_doctor(doctor_email)
        normalized = self._normalize_emails(patient_emails)
        if not normalized:
            raise UserNotFoundException("No s'ha trobat cap email de pacient vàlid per associar al doctor.")

        patients = self.patient_repo.fetch_by_emails(normalized)

        with self.uow:
            doctor.add_patients(patients)
            self.doctor_repo.update(doctor)

            for patient in patients:
                if doctor.email not in patient.doctor_emails:
                    patient.add_doctors([doctor])
                self.patient_repo.update(patient)

            self.uow.commit()

        return doctor

    def remove_patients(self, doctor_email: str, patient_emails: list[str]) -> Doctor:
        """
        Remove associations between a doctor and multiple patients.
        """
        doctor = self.get_doctor(doctor_email)
        normalized = self._normalize_emails(patient_emails)
        if not normalized:
            raise UserNotFoundException("No s'ha proporcionat cap correu electrònic de pacient vàlid per eliminar l'associació.")

        patients = self.patient_repo.fetch_by_emails(normalized)

        with self.uow:
            for patient in patients:
                doctor.remove_patient(patient.email)
                patient.remove_doctor(doctor.email)
                self.patient_repo.update(patient)

            self.doctor_repo.update(doctor)
            self.uow.commit()

        return doctor

    @staticmethod
    def _normalize_emails(emails: list[str] | None) -> list[str]:
        if not emails:
            return []
        seen = set()
        ordered: list[str] = []
        for email in emails:
            if not email:
                continue
            lowered = email.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            ordered.append(lowered)
        return ordered

    @staticmethod
    def _parse_gender(value: Gender | str) -> Gender:
        if isinstance(value, Gender):
            return value
        if isinstance(value, str):
            try:
                return Gender(value)
            except ValueError:
                return Gender[value.upper()]
        accepted_values = ", ".join([g.value for g in Gender])
        raise ValueError(f"Gènere no vàlid. Valors acceptats: {accepted_values}.")
