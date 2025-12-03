from __future__ import annotations

import uuid
from typing import Optional

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
    RelatedUserNotFoundException,
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

        # Base fields
        if "name" in update_data and update_data["name"] is not None:
            user.name = update_data["name"]
        if "surname" in update_data and update_data["surname"] is not None:
            user.surname = update_data["surname"]
        if "password" in update_data and update_data["password"] is not None:
            user.set_password(update_data["password"], self.hasher)

        if isinstance(user, Patient):
            if "ailments" in update_data:
                user.ailments = update_data.get("ailments")
            if "gender" in update_data and update_data["gender"] is not None:
                user.gender = update_data["gender"]
            if "age" in update_data and update_data["age"] is not None:
                user.age = update_data["age"]
            if "treatments" in update_data:
                user.treatments = update_data.get("treatments")
            if "height_cm" in update_data and update_data["height_cm"] is not None:
                user.height_cm = update_data["height_cm"]
            if "weight_kg" in update_data and update_data["weight_kg"] is not None:
                user.weight_kg = update_data["weight_kg"]
            if "doctors" in update_data:
                doctors_list = update_data.get("doctors") or []
                # Validate doctors exist (even if empty)
                self.doctor_repo.fetch_by_emails(doctors_list)
                user.replace_doctors(doctors_list)
            with self.uow:
                self.patient_repo.update(user)
                self.uow.commit()
        elif isinstance(user, Doctor):
            if "patients" in update_data:
                patients_list = update_data.get("patients") or []
                self.patient_repo.fetch_by_emails(patients_list)
                user.replace_patients(patients_list)
            with self.uow:
                self.doctor_repo.update(user)
                self.uow.commit()
        elif isinstance(user, Admin):
            with self.uow:
                self.admin_repo.update(user)
                self.uow.commit()
        else:
            raise UserRoleConflictException("L'usuari ha de tenir assignat exactament un únic rol.")
        return user

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
