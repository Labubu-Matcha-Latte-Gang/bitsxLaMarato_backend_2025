from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, List, Optional
import uuid

from domain.entities.score import Score
from domain.entities.user import User, Patient, Doctor, Admin
from domain.entities.question import Question
from domain.entities.question_answer import QuestionAnswer
from domain.entities.activity import Activity
from domain.entities.transcription_analysis import TranscriptionAnalysis


class IUserRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email.

        Args:
            email (str): Email identifier.

        Returns:
            Optional[User]: The matching user or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def add(self, user: User) -> None:
        """
        Persist a new user aggregate.

        Args:
            user (User): User entity to add.
        """
        raise NotImplementedError()

    @abstractmethod
    def update(self, user: User) -> None:
        """
        Persist changes to an existing user.

        Args:
            user (User): Updated user entity.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove(self, user: User) -> None:
        """
        Delete a user.

        Args:
            user (User): User entity to delete.
        """
        raise NotImplementedError()


class IPatientRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Patient]:
        """
        Retrieve a patient by email.

        Args:
            email (str): Email identifier.

        Returns:
            Optional[Patient]: Matching patient or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def add(self, patient: Patient) -> None:
        """
        Persist a new patient.

        Args:
            patient (Patient): Patient entity to add.
        """
        raise NotImplementedError()

    @abstractmethod
    def update(self, patient: Patient) -> None:
        """
        Persist changes to a patient.

        Args:
            patient (Patient): Updated patient entity.
        """
        raise NotImplementedError()

    @abstractmethod
    def fetch_by_emails(self, emails: Iterable[str]) -> List[Patient]:
        """
        Retrieve multiple patients by email list.

        Args:
            emails (Iterable[str]): Emails to resolve.

        Returns:
            List[Patient]: Found patients. Implementations should raise if any are missing.
        """
        raise NotImplementedError()


class IDoctorRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Doctor]:
        """
        Retrieve a doctor by email.

        Args:
            email (str): Email identifier.

        Returns:
            Optional[Doctor]: Matching doctor or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def add(self, doctor: Doctor) -> None:
        """
        Persist a new doctor.

        Args:
            doctor (Doctor): Doctor entity to add.
        """
        raise NotImplementedError()

    @abstractmethod
    def update(self, doctor: Doctor) -> None:
        """
        Persist changes to a doctor.

        Args:
            doctor (Doctor): Updated doctor entity.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove(self, doctor: Doctor) -> None:
        """
        Delete a doctor.

        Args:
            doctor (Doctor): Doctor entity to delete.
        """
        raise NotImplementedError()

    @abstractmethod
    def fetch_by_emails(self, emails: Iterable[str]) -> List[Doctor]:
        """
        Retrieve multiple doctors by email list.

        Args:
            emails (Iterable[str]): Emails to resolve.

        Returns:
            List[Doctor]: Found doctors. Implementations should raise if any are missing.
        """
        raise NotImplementedError()


class IAdminRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Admin]:
        """
        Retrieve an admin by email.

        Args:
            email (str): Email identifier.

        Returns:
            Optional[Admin]: Matching admin or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def add(self, admin: Admin) -> None:
        """
        Persist a new admin.

        Args:
            admin (Admin): Admin entity to add.
        """
        raise NotImplementedError()

    @abstractmethod
    def update(self, admin: Admin) -> None:
        """
        Persist changes to an admin.

        Args:
            admin (Admin): Updated admin entity.
        """
        raise NotImplementedError()


class IQuestionRepository(ABC):
    @abstractmethod
    def get(self, question_id: uuid.UUID) -> Optional[Question]:
        """
        Retrieve a question by ID.

        Args:
            question_id (uuid.UUID): Identifier of the question.

        Returns:
            Optional[Question]: Matching question or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def list(self, filters: dict) -> List[Question]:
        """
        List questions matching optional filters.

        Args:
            filters (dict): Filtering criteria.

        Returns:
            List[Question]: Questions satisfying the filters.
        """
        raise NotImplementedError()

    @abstractmethod
    def add_many(self, questions: Iterable[Question]) -> None:
        """
        Persist multiple questions.

        Args:
            questions (Iterable[Question]): Questions to add.
        """
        raise NotImplementedError()

    @abstractmethod
    def update(self, question: Question) -> None:
        """
        Persist changes to a question.

        Args:
            question (Question): Updated question entity.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove(self, question: Question) -> None:
        """
        Delete a question.

        Args:
            question (Question): Question to delete.
        """
        raise NotImplementedError()


class IActivityRepository(ABC):
    @abstractmethod
    def get(self, activity_id: uuid.UUID) -> Optional[Activity]:
        """
        Retrieve an activity by ID.

        Args:
            activity_id (uuid.UUID): Identifier of the activity.

        Returns:
            Optional[Activity]: Matching activity or None.
        """
        raise NotImplementedError()

    @abstractmethod
    def list(self, filters: dict) -> List[Activity]:
        """
        List activities matching optional filters.

        Args:
            filters (dict): Filtering criteria.

        Returns:
            List[Activity]: Activities satisfying the filters.
        """
        raise NotImplementedError()

    @abstractmethod
    def add_many(self, activities: Iterable[Activity]) -> None:
        """
        Persist multiple activities.

        Args:
            activities (Iterable[Activity]): Activities to add.
        """
        raise NotImplementedError()

    @abstractmethod
    def update(self, activity: Activity) -> None:
        """
        Persist changes to an activity.

        Args:
            activity (Activity): Updated activity entity.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove(self, activity: Activity) -> None:
        """
        Delete an activity.

        Args:
            activity (Activity): Activity to delete.
        """
        raise NotImplementedError()


class IResetCodeRepository(ABC):
    @abstractmethod
    def save_code(self, email: str, hashed_code: str, expiration: datetime) -> None:
        """
        Persist or replace a reset code for a user.

        Args:
            email (str): Target user email.
            hashed_code (str): Hashed reset code.
            expiration (datetime): Expiration timestamp.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_code(self, email: str) -> Optional[tuple[str, datetime]]:
        """
        Returns (hashed_code, expiration) or None.

        Args:
            email (str): Target user email.

        Returns:
            Optional[tuple[str, datetime]]: Stored code hash and expiration, if any.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_code(self, email: str) -> None:
        """
        Delete a stored reset code for a user.

        Args:
            email (str): Target user email.
        """
        raise NotImplementedError()


class ITranscriptionAnalysisRepository(ABC):
    """
    Repository abstraction for retrieving cognitive analysis sessions linked
    to patients.  These sessions encapsulate metrics derived from voice
    transcriptions (e.g., processing speed, lexical access) and are used
    by recommendation strategies to adjust difficulty and content.

    The application layer uses this interface to fetch all sessions of a
    given patient.  Infrastructure implementations should persist and
    return domain-level ``TranscriptionAnalysis`` objects.
    """

    @abstractmethod
    def list_by_patient(self, patient_email: str) -> List[TranscriptionAnalysis]:
        """
        List all transcription analysis sessions for a given patient.

        Args:
            patient_email (str): The unique email of the patient whose
                sessions are requested.

        Returns:
            List[TranscriptionAnalysis]: A list of domain objects representing
                each cognitive analysis session, or an empty list if none exist.
        """
        raise NotImplementedError()

class IScoreRepository(ABC):
    @abstractmethod
    def add(self, score: Score) -> None:
        """
        Persist a new score.

        Args:
            score (Score): Score entity to add.
        """
        raise NotImplementedError()
    
    @abstractmethod
    def list_by_patient(self, patient_email: str) -> List[Score]:
        """
        List scores for a given patient.

        Args:
            patient_email (str): Email of the patient.
        Returns:
            List[Score]: List of scores for the patient.
        """
        raise NotImplementedError()


class IQuestionAnswerRepository(ABC):
    """
    Repository abstraction for retrieving answered questions.  The
    application layer uses this interface to fetch the relationship between
    a patient and the questions they have answered, along with any
    associated analysis metrics.
    """

    @abstractmethod
    def list_by_patient(self, patient_email: str) -> List["QuestionAnswer"]:
        """
        List all questions answered by a given patient.

        Implementations should return domain-level ``QuestionAnswer`` objects,
        containing the question, the timestamp of the answer and any analysis
        metrics captured at answer time.

        Args:
            patient_email (str): The unique email of the patient whose
                answered questions are requested.

        Returns:
            List[QuestionAnswer]: A list of domain objects representing each
                answered question.
        """
        raise NotImplementedError()