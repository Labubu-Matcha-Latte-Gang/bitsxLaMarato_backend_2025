from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

from domain.entities.user import User
from domain.repositories import IResetCodeRepository, IUserRepository
from domain.services.security import PasswordHasher
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.user_exceptions import (
    InvalidResetCodeException,
    UserNotFoundException,
)


class PasswordResetService:
    def __init__(
        self,
        user_repo: IUserRepository,
        code_repo: IResetCodeRepository,
        hasher: PasswordHasher,
        uow: IUnitOfWork,
        validity_minutes: int,
    ):
        self.user_repo = user_repo
        self.code_repo = code_repo
        self.hasher = hasher
        self.uow = uow
        self.validity_minutes = validity_minutes

    def generate_reset_code(self, email: str) -> str:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundException(f"No s'ha trobat cap usuari amb el correu {email}.")

        reset_code = self._random_code()
        hashed_code = self.hasher.hash(reset_code)
        expiration = datetime.now(timezone.utc) + timedelta(minutes=self.validity_minutes)

        with self.uow:
            self.code_repo.save_code(email, hashed_code, expiration)
            self.uow.commit()
        return reset_code

    def reset_password(self, email: str, reset_code: str, new_password: str) -> None:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundException(f"No s'ha trobat cap usuari amb el correu {email}.")

        stored = self.code_repo.get_code(email)
        if stored is None:
            raise InvalidResetCodeException("El codi de restabliment proporcionat no és vàlid o ha caducat.")
        hashed_code, expiration = stored

        now = datetime.now(timezone.utc)
        if now >= self._ensure_aware(expiration):
            with self.uow:
                self.code_repo.delete_code(email)
                self.uow.commit()
            raise InvalidResetCodeException("El codi de restabliment proporcionat no és vàlid o ha caducat.")

        if not self.hasher.verify(reset_code, hashed_code):
            raise InvalidResetCodeException("El codi de restabliment proporcionat no és vàlid o ha caducat.")

        user.set_password(new_password, self.hasher)
        with self.uow:
            self.user_repo.update(user)
            self.code_repo.delete_code(email)
            self.uow.commit()

    def _random_code(self) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(8))

    def _ensure_aware(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
