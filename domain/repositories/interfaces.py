from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, List, Optional
import uuid

from domain.entities.user import User, Patient, Doctor, Admin
from domain.entities.question import Question
from domain.entities.activity import Activity


class IUserRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError()

    @abstractmethod
    def add(self, user: User) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update(self, user: User) -> None:
        raise NotImplementedError()

    @abstractmethod
    def remove(self, user: User) -> None:
        raise NotImplementedError()


class IPatientRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Patient]:
        raise NotImplementedError()

    @abstractmethod
    def add(self, patient: Patient) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update(self, patient: Patient) -> None:
        raise NotImplementedError()

    @abstractmethod
    def fetch_by_emails(self, emails: Iterable[str]) -> List[Patient]:
        raise NotImplementedError()


class IDoctorRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Doctor]:
        raise NotImplementedError()

    @abstractmethod
    def add(self, doctor: Doctor) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update(self, doctor: Doctor) -> None:
        raise NotImplementedError()

    @abstractmethod
    def fetch_by_emails(self, emails: Iterable[str]) -> List[Doctor]:
        raise NotImplementedError()


class IAdminRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Admin]:
        raise NotImplementedError()

    @abstractmethod
    def add(self, admin: Admin) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update(self, admin: Admin) -> None:
        raise NotImplementedError()


class IQuestionRepository(ABC):
    @abstractmethod
    def get(self, question_id: uuid.UUID) -> Optional[Question]:
        raise NotImplementedError()

    @abstractmethod
    def list(self, filters: dict) -> List[Question]:
        raise NotImplementedError()

    @abstractmethod
    def add_many(self, questions: Iterable[Question]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update(self, question: Question) -> None:
        raise NotImplementedError()

    @abstractmethod
    def remove(self, question: Question) -> None:
        raise NotImplementedError()


class IActivityRepository(ABC):
    @abstractmethod
    def get(self, activity_id: uuid.UUID) -> Optional[Activity]:
        raise NotImplementedError()

    @abstractmethod
    def list(self, filters: dict) -> List[Activity]:
        raise NotImplementedError()

    @abstractmethod
    def add_many(self, activities: Iterable[Activity]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update(self, activity: Activity) -> None:
        raise NotImplementedError()

    @abstractmethod
    def remove(self, activity: Activity) -> None:
        raise NotImplementedError()


class IResetCodeRepository(ABC):
    @abstractmethod
    def save_code(self, email: str, hashed_code: str, expiration: datetime) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_code(self, email: str) -> Optional[tuple[str, datetime]]:
        """
        Returns (hashed_code, expiration) or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_code(self, email: str) -> None:
        raise NotImplementedError()
