from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Dict

from domain.entities.user import Admin, Doctor, Patient, User
from domain.repositories import (
    IAdminRepository,
    IDoctorRepository,
    IPatientRepository,
    IUserRepository,
)
from domain.services.security import PasswordHasher
from domain.unit_of_work import IUnitOfWork
from helpers.enums.gender import Gender
from helpers.enums.user_role import UserRole
from helpers.exceptions.user_exceptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
    UserRoleConflictException,
)
from application.services.token_service import TokenService


class UserService:
    def __init__(
        self,
        user_repo: IUserRepository,
        patient_repo: IPatientRepository,
        doctor_repo: IDoctorRepository,
        admin_repo: IAdminRepository,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
        token_service: TokenService,
    ):
        self.user_repo = user_repo
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo
        self.admin_repo = admin_repo
        self.uow = uow
        self.hasher = hasher
        self.token_service = token_service

    def register_patient(self, data: dict) -> Patient:
        email = data["email"]
        if self.user_repo.get_by_email(email):
            raise UserAlreadyExistsException("Ja existeix un usuari amb aquest correu.")

        doctor_emails = data.get("doctors", []) or []
        if doctor_emails:
            # Validate related doctors exist
            self.doctor_repo.fetch_by_emails(doctor_emails)

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
            self.uow.commit()
        return patient

    def register_doctor(self, data: dict) -> Doctor:
        email = data["email"]
        if self.user_repo.get_by_email(email):
            raise UserAlreadyExistsException("Ja existeix un usuari amb aquest correu.")

        patient_emails = data.get("patients", []) or []
        if patient_emails:
            self.patient_repo.fetch_by_emails(patient_emails)

        doctor = Doctor(
            email=email,
            password_hash=self.hasher.hash(data["password"]),
            name=data["name"],
            surname=data["surname"],
            patient_emails=list(patient_emails),
        )
        with self.uow:
            self.doctor_repo.add(doctor)
            self.uow.commit()
        return doctor

    def register_admin(self, email: str, password: str, name: str, surname: str) -> Admin:
        if self.user_repo.get_by_email(email):
            raise UserAlreadyExistsException("Ja existeix un usuari amb aquest correu.")
        admin = Admin(
            email=email,
            password_hash=self.hasher.hash(password),
            name=name,
            surname=surname,
        )
        with self.uow:
            self.admin_repo.add(admin)
            self.uow.commit()
        return admin

    def login(self, email: str, password: str) -> str:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise InvalidCredentialsException("Correu o contrasenya no vàlids.")
        if not user.check_password(password, self.hasher):
            raise InvalidCredentialsException("Correu o contrasenya no vàlids.")
        token = self.token_service.generate(user.email)
        return token

    def get_user(self, email: str) -> User:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundException("Usuari no trobat.")
        return user

    def update_user(self, email: str, update_data: dict) -> User:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundException("Usuari no trobat.")

        updater = self._build_role_updater(user.role)
        return updater.update(user, update_data)

    def delete_user(self, email: str) -> None:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundException("Usuari no trobat.")
        with self.uow:
            self.user_repo.remove(user)
            self.uow.commit()

    def get_patient_data(self, requester_email: str, patient_email: str) -> Patient:
        requester = self.user_repo.get_by_email(requester_email)
        if requester is None:
            raise UserNotFoundException("Usuari no trobat.")
        patient = self.patient_repo.get_by_email(patient_email)
        if patient is None:
            raise UserNotFoundException("Pacient no trobat.")

        if isinstance(requester, Admin):
            return patient
        if isinstance(requester, Doctor) and patient.email in requester.patient_emails:
            return patient
        if isinstance(requester, Patient) and requester.email == patient.email:
            return patient
        raise PermissionError("No tens permís per accedir a les dades d'aquest pacient.")

    def _build_role_updater(self, role: UserRole) -> "_BaseRoleUpdater":
        """
        Factory for role-specific update handlers.

        Args:
            role (UserRole): Role of the user being updated.

        Returns:
            _BaseRoleUpdater: Handler that knows how to mutate and persist the role.

        Raises:
            UserRoleConflictException: If the role is unsupported.
        """
        updaters: Dict[UserRole, _BaseRoleUpdater] = {
            UserRole.PATIENT: _PatientUpdater(
                self.patient_repo,
                self.doctor_repo,
                self.uow,
                self.hasher,
            ),
            UserRole.DOCTOR: _DoctorUpdater(
                self.doctor_repo,
                self.patient_repo,
                self.uow,
                self.hasher,
            ),
            UserRole.ADMIN: _AdminUpdater(
                self.admin_repo,
                self.uow,
                self.hasher,
            ),
        }
        try:
            return updaters[role]
        except KeyError as exc:
            raise UserRoleConflictException("L'usuari ha de tenir assignat exactament un únic rol.") from exc


class _BaseRoleUpdater(ABC):
    def __init__(self, uow: IUnitOfWork, hasher: PasswordHasher) -> None:
        self.uow = uow
        self.hasher = hasher

    def _update_common_fields(self, user: User, update_data: dict) -> None:
        """Update base user fields."""
        base_fields = {k: v for k, v in update_data.items() if k in {"name", "surname", "password"}}
        if base_fields.get("password") is not None:
            user.set_password(base_fields["password"], self.hasher)
        if base_fields.get("name") is not None:
            user.name = base_fields["name"]
        if base_fields.get("surname") is not None:
            user.surname = base_fields["surname"]

    @abstractmethod
    def update(self, user: User, update_data: dict) -> User:
        ...


class _PatientUpdater(_BaseRoleUpdater):
    def __init__(
        self,
        patient_repo: IPatientRepository,
        doctor_repo: IDoctorRepository,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
    ) -> None:
        super().__init__(uow, hasher)
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo

    def update(self, user: User, update_data: dict) -> Patient:
        patient: Patient = user
        doctors_list = update_data.get("doctors")
        if doctors_list is not None:
            normalized = doctors_list or []
            self.doctor_repo.fetch_by_emails(normalized)
            update_data = {**update_data, "doctors": normalized}

        self._update_common_fields(patient, update_data)
        patient.set_properties(update_data, self.hasher)

        with self.uow:
            self.patient_repo.update(patient)
            self.uow.commit()
        return patient


class _DoctorUpdater(_BaseRoleUpdater):
    def __init__(
        self,
        doctor_repo: IDoctorRepository,
        patient_repo: IPatientRepository,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
    ) -> None:
        super().__init__(uow, hasher)
        self.doctor_repo = doctor_repo
        self.patient_repo = patient_repo

    def update(self, user: User, update_data: dict) -> Doctor:
        doctor: Doctor = user
        patients_list = update_data.get("patients")
        if patients_list is not None:
            normalized = patients_list or []
            self.patient_repo.fetch_by_emails(normalized)
            update_data = {**update_data, "patients": normalized}

        self._update_common_fields(doctor, update_data)
        doctor.set_properties(update_data, self.hasher)

        with self.uow:
            self.doctor_repo.update(doctor)
            self.uow.commit()
        return doctor


class _AdminUpdater(_BaseRoleUpdater):
    def __init__(
        self,
        admin_repo: IAdminRepository,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
    ) -> None:
        super().__init__(uow, hasher)
        self.admin_repo = admin_repo

    def update(self, user: User, update_data: dict) -> Admin:
        admin: Admin = user
        self._update_common_fields(admin, update_data)
        admin.set_properties(update_data, self.hasher)

        with self.uow:
            self.admin_repo.update(admin)
            self.uow.commit()
        return admin
