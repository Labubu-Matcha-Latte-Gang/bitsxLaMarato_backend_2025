from __future__ import annotations

from typing import Optional

from db import db
from application.services import (
    ActivityService,
    AdminService,
    DoctorService,
    ScoreService,
    PasswordResetService,
    PatientService,
    QuestionService,
    TokenService,
    UserService,
)
from domain.services.security import PasswordHasher
from infrastructure.sqlalchemy import (
    SQLAlchemyActivityRepository,
    SQLAlchemyAdminRepository,
    SQLAlchemyDoctorRepository,
    SQLAlchemyPatientRepository,
    SQLAlchemyQuestionRepository,
    SQLAlchemyQuestionAnswerRepository,
    SQLAlchemyScoreRepository,
    SQLAlchemyResetCodeRepository,
    SQLAlchemyUnitOfWork,
    SQLAlchemyUserRepository,
)
from helpers.plotly_adapter import SimplePlotlyAdapter
from sqlalchemy.orm import Session


class ServiceFactory:
    """
    Simple factory that builds service instances with their dependencies.
    Exposed as a singleton to share wiring (session, repos, UoW) across layers.
    """
    __instance: 'ServiceFactory' | None = None

    def __init__(self, session: Optional[Session] = None):
        self.session: Session = session or db.session

    @classmethod
    def get_instance(cls, session: Optional[Session] = None, refresh: bool = False) -> 'ServiceFactory':
        """
        Return the singleton instance. Optionally refresh or inject a session.
        Args:
            session (Optional[Session]): SQLAlchemy session to use.
            refresh (bool): If True, forces creation of a new instance.
        Returns:
            ServiceFactory: The singleton instance.
        """
        if refresh or cls.__instance is None or (session is not None and cls.__instance.session is not session):
            cls.__instance = cls(session)
        return cls.__instance

    def build_user_service(self) -> UserService:
        """
        Build a UserService with its dependencies.
        Returns:
            UserService: The constructed UserService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        hasher = PasswordHasher()
        token_service = TokenService()

        user_repo = SQLAlchemyUserRepository(self.session)
        # Build subordinate services
        patient_service = PatientService(
            user_repo=user_repo,
            patient_repo=SQLAlchemyPatientRepository(self.session),
            doctor_repo=SQLAlchemyDoctorRepository(self.session),
            uow=SQLAlchemyUnitOfWork(self.session),
            hasher=hasher,
        )
        doctor_service = DoctorService(
            user_repo=user_repo,
            doctor_repo=SQLAlchemyDoctorRepository(self.session),
            patient_repo=SQLAlchemyPatientRepository(self.session),
            uow=SQLAlchemyUnitOfWork(self.session),
            hasher=hasher,
        )
        admin_service = AdminService(
            user_repo=user_repo,
            admin_repo=SQLAlchemyAdminRepository(self.session),
            uow=SQLAlchemyUnitOfWork(self.session),
            hasher=hasher,
        )

        # Additional repositories used directly by UserService
        score_repo = SQLAlchemyScoreRepository(self.session)
        question_answer_repo = SQLAlchemyQuestionAnswerRepository(self.session)
        plotly_adapter = SimplePlotlyAdapter()

        return UserService(
            user_repo=user_repo,
            patient_service=patient_service,
            doctor_service=doctor_service,
            admin_service=admin_service,
            uow=uow,
            hasher=hasher,
            token_service=token_service,
            score_repo=score_repo,
            question_answer_repo=question_answer_repo,
            plotly_adapter=plotly_adapter,
        )

    def build_question_service(self) -> QuestionService:
        """
        Build a QuestionService with its dependencies.
        Returns:
            QuestionService: The constructed QuestionService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        question_repo = SQLAlchemyQuestionRepository(self.session)
        return QuestionService(question_repo=question_repo, uow=uow)

    def build_activity_service(self) -> ActivityService:
        """
        Build an ActivityService with its dependencies.
        Returns:
            ActivityService: The constructed ActivityService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        activity_repo = SQLAlchemyActivityRepository(self.session)
        return ActivityService(activity_repo=activity_repo, uow=uow)

    def build_patient_service(self) -> PatientService:
        """
        Build a PatientService with its dependencies.
        Returns:
            PatientService: The constructed PatientService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        hasher = PasswordHasher()
        user_repo = SQLAlchemyUserRepository(self.session)
        patient_repo = SQLAlchemyPatientRepository(self.session)
        doctor_repo = SQLAlchemyDoctorRepository(self.session)
        return PatientService(
            user_repo=user_repo,
            patient_repo=patient_repo,
            doctor_repo=doctor_repo,
            uow=uow,
            hasher=hasher,
        )

    def build_doctor_service(self) -> DoctorService:
        """
        Build a DoctorService with its dependencies.
        Returns:
            DoctorService: The constructed DoctorService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        hasher = PasswordHasher()
        user_repo = SQLAlchemyUserRepository(self.session)
        doctor_repo = SQLAlchemyDoctorRepository(self.session)
        patient_repo = SQLAlchemyPatientRepository(self.session)
        return DoctorService(
            user_repo=user_repo,
            doctor_repo=doctor_repo,
            patient_repo=patient_repo,
            uow=uow,
            hasher=hasher,
        )

    def build_admin_service(self) -> AdminService:
        """
        Build an AdminService with its dependencies.
        Returns:
            AdminService: The constructed AdminService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        hasher = PasswordHasher()
        user_repo = SQLAlchemyUserRepository(self.session)
        admin_repo = SQLAlchemyAdminRepository(self.session)
        return AdminService(
            user_repo=user_repo,
            admin_repo=admin_repo,
            uow=uow,
            hasher=hasher,
        )

    def build_password_reset_service(self, validity_minutes: int) -> PasswordResetService:
        """
        Build a PasswordResetService with its dependencies.
        Args:
            validity_minutes (int): The validity duration for reset codes in minutes.
        Returns:
            PasswordResetService: The constructed PasswordResetService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        hasher = PasswordHasher()
        user_repo = SQLAlchemyUserRepository(self.session)
        code_repo = SQLAlchemyResetCodeRepository(self.session)
        return PasswordResetService(
            user_repo=user_repo,
            code_repo=code_repo,
            hasher=hasher,
            uow=uow,
            validity_minutes=validity_minutes,
        )

    def build_score_service(self) -> ScoreService:
        """
        Build a ScoreService with its dependencies.
        Returns:
            ScoreService: The constructed ScoreService instance.
        """
        uow = SQLAlchemyUnitOfWork(self.session)
        score_repo = SQLAlchemyScoreRepository(self.session)
        return ScoreService(
            score_repo=score_repo,
            uow=uow,
        )
