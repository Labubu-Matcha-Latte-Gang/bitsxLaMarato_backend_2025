from __future__ import annotations

import base64
import json
from pathlib import Path

from typing import Dict

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
from helpers.factories.adapter_factories import AbstractAdapterFactory
from models.associations import DoctorPatientAssociation, QuestionAnsweredAssociation, UserCodeAssociation
from models.doctor import Doctor as DoctorModel
from models.patient import Patient as PatientModel
from models.score import Score
from models.user import User as UserModel


class UserService:
    """
    Application service for user-level concerns (auth, user dispatch).
    Delegates role-specific operations to dedicated services.
    """

    GRAPH_TMP_DIR = Path(__file__).resolve().parent.parent.parent / "tmp"

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
        adapter_factory: AbstractAdapterFactory,
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
        self.adapter_factory = adapter_factory

    def register_patient(self, data: dict) -> Patient:
        return self.patient_service.register_patient(data)

    def register_doctor(self, data: dict) -> Doctor:
        return self.doctor_service.register_doctor(data)

    def register_admin(self, email: str, password: str, name: str, surname: str) -> Admin:
        return self.admin_service.register_admin(email, password, name, surname)

    def login(self, email: str, password: str) -> str:
        user = self.user_repo.get_by_email(email)
        if user is None:
            raise InvalidCredentialsException("Correu o contrassenya no vàlids.")
        if not user.check_password(password, self.hasher):
            raise InvalidCredentialsException("Correu o contrassenya no vàlids.")
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

        # Perform explicit clean-up to avoid relying on DB ON DELETE cascades.
        session = getattr(self.uow, "session", None)
        with self.uow:
            if session is not None:
                # Remove reset codes linked to this user.
                session.query(UserCodeAssociation).filter(UserCodeAssociation.user_email == email).delete(
                    synchronize_session=False
                )

                if isinstance(user, Patient):
                    session.query(DoctorPatientAssociation).filter(
                        DoctorPatientAssociation.patient_email == email
                    ).delete(synchronize_session=False)
                    session.query(QuestionAnsweredAssociation).filter(
                        QuestionAnsweredAssociation.patient_email == email
                    ).delete(synchronize_session=False)
                    session.query(Score).filter(Score.patient_email == email).delete(
                        synchronize_session=False
                    )
                    patient_model = session.get(PatientModel, email)
                    if patient_model:
                        session.delete(patient_model)
                elif isinstance(user, Doctor):
                    session.query(DoctorPatientAssociation).filter(
                        DoctorPatientAssociation.doctor_email == email
                    ).delete(synchronize_session=False)
                    doctor_model = session.get(DoctorModel, email)
                    if doctor_model:
                        session.delete(doctor_model)
                else:
                    user_model = session.get(UserModel, email)
                    if user_model:
                        session.delete(user_model)
            else:
                # Fallback for unit of work implementations without direct session access.
                self.user_repo.remove(user)
            self.uow.commit()

    def get_patient_data(self, requester: User, patient: Patient) -> dict:
        """
        Assemble a comprehensive payload for the given patient including basic
        demographics, activity scores, answered questions and generated graph
        files. The caller must supply a user (requester) authorized to view the
        patient.

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
                - ``graph_files``: fragments HTML (div + script Plotly) codificats en base64; es poden injectar des de frontend (p. ex. WebView de Flutter via ``loadHtmlString``).

        Raises:
            PermissionError: If the requester is not authorized to view the
                patient's data.
        """
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

        patient_payload = patient.to_dict()

        try:
            score_objects = self.score_repo.list_by_patient(patient.email)
        except Exception:
            score_objects = []
        scores_list = []
        for score in score_objects:
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
        graphic_adapter = self.adapter_factory.get_graphic_adapter()
        try:
            graphs.update(graphic_adapter.create_score_graphs(score_objects))
            graphs.update(graphic_adapter.create_question_graphs(answered))
        except Exception:
            # Graph generation is optional; if it fails, leave graphs empty
            graphs = {}

        graph_files: list[dict] = []
        if graphs:
            try:
                graph_files = self._build_graph_files(graphs)
            except Exception:
                graph_files = []

        return {
            "patient": patient_payload,
            "scores": scores_list,
            "questions": questions_list,
            "graph_files": graph_files,
        }

    def _build_graph_files(self, graphs: Dict[str, dict]) -> list[dict]:
        """
        Persist graph figures as HTML fragments in the tmp directory and return
        them as base64-encoded payloads. All files in the tmp directory are
        removed once the payload is built.
        """
        self.GRAPH_TMP_DIR.mkdir(parents=True, exist_ok=True)

        created_files: list[dict] = []
        try:
            for name, figure in graphs.items():
                sanitized_name = name.replace(" ", "_")
                file_path = self.GRAPH_TMP_DIR / f"{sanitized_name}.html"
                html_content = self._figure_to_html(name, figure)
                file_path.write_text(html_content, encoding="utf-8")
                encoded_content = base64.b64encode(file_path.read_bytes()).decode("ascii")
                created_files.append({
                    "filename": file_path.name,
                    "content_type": "text/html",
                    "content": encoded_content,
                })
            return created_files
        finally:
            self._cleanup_tmp_graph_dir()

    def _figure_to_html(self, title: str, figure: dict) -> str:
        """
        Render an embeddable HTML fragment (div + script) for Plotly.

        The fragment loads Plotly from CDN only if it is not already present in
        the embedding document. It is intended to be consumed as `srcdoc` of an
        <iframe> or injected into a wrapper element that allows script
        execution.
        """
        figure_id = f"plot_{title}".replace(" ", "_").replace("-", "_")
        data_json = json.dumps(figure.get("data", []))
        layout = figure.get("layout", {}) or {}
        layout.setdefault("title", title)
        layout_json = json.dumps(layout)
        return f"""<div id="{figure_id}" style="width:100%;min-height:360px;"></div>
<script>
(function() {{
  const render = () => Plotly.newPlot("{figure_id}", {data_json}, {layout_json}, {{responsive: true}});
  if (window.Plotly) {{
    render();
    return;
  }}
  const script = document.createElement("script");
  script.src = "https://cdn.plot.ly/plotly-latest.min.js";
  script.onload = render;
  document.head.appendChild(script);
}})();
</script>"""

    def _cleanup_tmp_graph_dir(self) -> None:
        """
        Remove all files inside the graph tmp directory.
        """
        if not self.GRAPH_TMP_DIR.exists():
            return
        for file in self.GRAPH_TMP_DIR.iterdir():
            if file.is_file():
                file.unlink(missing_ok=True)
