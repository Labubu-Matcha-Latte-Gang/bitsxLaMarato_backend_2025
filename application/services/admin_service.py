from __future__ import annotations

from domain.entities.user import Admin
from domain.repositories import IAdminRepository, IUserRepository
from domain.services.security import PasswordHasher
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.user_exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
)


class AdminService:
    """
    Application service for administrator-specific operations.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        admin_repo: IAdminRepository,
        uow: IUnitOfWork,
        hasher: PasswordHasher,
    ) -> None:
        self.user_repo = user_repo
        self.admin_repo = admin_repo
        self.uow = uow
        self.hasher = hasher

    def register_admin(self, email: str, password: str, name: str, surname: str) -> Admin:
        """
        Create an administrator user.
        """
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

    def get_admin(self, email: str) -> Admin:
        """
        Retrieve an admin by email or raise if it does not exist.
        """
        admin = self.admin_repo.get_by_email(email)
        if admin is None:
            raise UserNotFoundException("Administrador no trobat.")
        return admin

    def update_admin(self, email: str, update_data: dict) -> Admin:
        """
        Update admin profile data (name, surname, password) within a transaction.
        """
        admin = self.get_admin(email)
        admin.set_properties(update_data, self.hasher)

        with self.uow:
            self.admin_repo.update(admin)
            self.uow.commit()

        return admin
