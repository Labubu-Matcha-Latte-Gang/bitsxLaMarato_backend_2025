from __future__ import annotations

from db import db
from application.services import (
    ActivityService,
    PasswordResetService,
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
    SQLAlchemyResetCodeRepository,
    SQLAlchemyUnitOfWork,
    SQLAlchemyUserRepository,
)


class ServiceFactory:
    def __init__(self, session=None):
        self.session = session or db.session

    def build_user_service(self) -> UserService:
        uow = SQLAlchemyUnitOfWork(self.session)
        hasher = PasswordHasher()
        token_service = TokenService()

        user_repo = SQLAlchemyUserRepository(self.session)
        patient_repo = SQLAlchemyPatientRepository(self.session)
        doctor_repo = SQLAlchemyDoctorRepository(self.session)
        admin_repo = SQLAlchemyAdminRepository(self.session)

        return UserService(
            user_repo=user_repo,
            patient_repo=patient_repo,
            doctor_repo=doctor_repo,
            admin_repo=admin_repo,
            uow=uow,
            hasher=hasher,
            token_service=token_service,
        )

    def build_question_service(self) -> QuestionService:
        uow = SQLAlchemyUnitOfWork(self.session)
        question_repo = SQLAlchemyQuestionRepository(self.session)
        return QuestionService(question_repo=question_repo, uow=uow)

    def build_activity_service(self) -> ActivityService:
        uow = SQLAlchemyUnitOfWork(self.session)
        activity_repo = SQLAlchemyActivityRepository(self.session)
        return ActivityService(activity_repo=activity_repo, uow=uow)

    def build_password_reset_service(self, validity_minutes: int) -> PasswordResetService:
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
