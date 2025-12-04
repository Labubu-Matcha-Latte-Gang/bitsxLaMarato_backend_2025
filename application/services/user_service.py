from __future__ import annotations

from domain.entities.user import Admin, Doctor, Patient, User
from domain.repositories import IUserRepository
from domain.services.security import PasswordHasher
from domain.unit_of_work import IUnitOfWork
from helpers.enums.user_role import UserRole
from helpers.exceptions.user_exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
    UserRoleConflictException,
)
from application.services.admin_service import AdminService
from application.services.doctor_service import DoctorService
from application.services.patient_service import PatientService
from application.services.token_service import TokenService


class UserService:
    """
    Application service for user-level concerns (auth, user dispatch).
    Delegates role-specific operations to dedicated services.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        patient_service: PatientService,
        doctor_service: DoctorService,
        admin_service: AdminService,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
        token_service: TokenService,
    ):
        self.user_repo = user_repo
        self.patient_service = patient_service
        self.doctor_service = doctor_service
        self.admin_service = admin_service
        self.uow = uow
        self.hasher = hasher
        self.token_service = token_service

    def register_patient(self, data: dict) -> Patient:
        return self.patient_service.register_patient(data)

    def register_doctor(self, data: dict) -> Doctor:
        return self.doctor_service.register_doctor(data)

    def register_admin(self, email: str, password: str, name: str, surname: str) -> Admin:
        return self.admin_service.register_admin(email, password, name, surname)

    def login(self, email: str, password: str) -> str:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise InvalidCredentialsException("Correu o contrasenya no vàlids.")
        if not user.check_password(password, self.hasher):
            raise InvalidCredentialsException("Correu o contrasenya no vàlids.")
        return self.token_service.generate(user.email)

    def get_user(self, email: str) -> User:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundException("Usuari no trobat.")
        return user

    def update_user(self, email: str, update_data: dict) -> User:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundException("Usuari no trobat.")

        if user.role == UserRole.PATIENT:
            return self.patient_service.update_patient(email, update_data)
        if user.role == UserRole.DOCTOR:
            return self.doctor_service.update_doctor(email, update_data)
        if user.role == UserRole.ADMIN:
            return self.admin_service.update_admin(email, update_data)
        raise UserRoleConflictException("L'usuari ha de tenir assignat exactament un únic rol.")

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
        patient = self.patient_service.get_patient(patient_email)
        if patient is None:
            raise UserNotFoundException("Pacient no trobat.")

        if isinstance(requester, Admin):
            return patient
        if isinstance(requester, Doctor) and patient.email in requester.patient_emails:
            return patient
        if isinstance(requester, Patient) and requester.email == patient.email:
            return patient
        raise PermissionError("No tens permís per accedir a les dades d'aquest pacient.")
