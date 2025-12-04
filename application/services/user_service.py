from __future__ import annotations

from domain.entities.user import Admin, Doctor, Patient, User
from domain.repositories import (
    IUserRepository,
    IScoreRepository,
    IQuestionAnswerRepository,
)
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
from typing import Dict
from helpers.plotly_adapter import AbstractPlotlyAdapter


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
        score_repo: IScoreRepository,
        question_answer_repo: IQuestionAnswerRepository,
        plotly_adapter: AbstractPlotlyAdapter,
    ):
        self.user_repo = user_repo
        self.patient_service = patient_service
        self.doctor_service = doctor_service
        self.admin_service = admin_service
        self.uow = uow
        self.hasher = hasher
        self.token_service = token_service
        self.score_repo = score_repo
        self.question_answer_repo = question_answer_repo
        self.plotly_adapter = plotly_adapter

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

    def get_patient_data(self, requester: User, patient: Patient) -> dict:
        """
        Assemble a comprehensive payload for the given patient including basic
        demographics, activity scores, answered questions and graph
        definitions for Plotly.  The caller must supply a user (requester)
        authorized to view the patient.

        Args:
            requester (User): The user requesting the data.  Must be an admin,
                assigned doctor or the patient themselves.
            patient (Patient): The patient whose data is being requested.

        Returns:
            dict: A dictionary ready to be serialized as JSON containing:
                - ``patient``: basic patient information as returned by
                  ``Patient.to_dict()``.
                - ``scores``: list of score objects with activity metadata.
                - ``questions``: list of answered questions with analysis metrics.
                - ``graphs``: a mapping of Plotly-compatible chart definitions.

        Raises:
            PermissionError: If the requester is not authorized to view the
                patient's data.
        """
        # Authorization as in the original implementation
        if isinstance(requester, Admin):
            authorized = True
        elif isinstance(requester, Doctor) and patient.email in requester.patient_emails:
            authorized = True
        elif isinstance(requester, Patient) and requester.email == patient.email:
            authorized = True
        else:
            authorized = False
        if not authorized:
            raise PermissionError("No tens permís per accedir a les dades d'aquest pacient.")

        # Core patient information
        patient_payload = patient.to_dict()

        # Retrieve scores for this patient via the injected repository
        try:
            score_objects = self.score_repo.list_by_patient(patient.email)
        except Exception:
            score_objects = []
        scores_list = []
        for score in score_objects:
            # Flatten the score for API serialization
            scores_list.append({
                "activity_id": str(score.activity.id),
                "activity_title": score.activity.title,
                "activity_type": score.activity.activity_type.value if score.activity.activity_type else None,
                "completed_at": score.completed_at.isoformat(),
                "score": score.score,
                "seconds_to_finish": score.seconds_to_finish,
            })

        # Retrieve answered questions with metrics
        try:
            answered = self.question_answer_repo.list_by_patient(patient.email)
        except Exception:
            answered = []
        questions_list = [qa.to_dict() for qa in answered]

        # Build graph definitions using the adapter
        graphs: Dict[str, dict] = {}
        try:
            graphs.update(self.plotly_adapter.create_score_graphs(score_objects))
            graphs.update(self.plotly_adapter.create_question_graphs(answered))
        except Exception:
            # Graph generation is optional; if it fails, leave graphs empty
            graphs = {}

        return {
            "patient": patient_payload,
            "scores": scores_list,
            "questions": questions_list,
            "graphs": graphs,
        }
