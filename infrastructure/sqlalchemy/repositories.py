from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional
import uuid

from db import db
from domain.entities.activity import Activity as ActivityDomain
from domain.entities.question import Question as QuestionDomain
from domain.entities.user import Admin as AdminDomain
from domain.entities.user import Doctor as DoctorDomain
from domain.entities.user import Patient as PatientDomain
from domain.entities.user import User as UserDomain
from domain.repositories import (
    IActivityRepository,
    IAdminRepository,
    IDoctorRepository,
    IPatientRepository,
    IQuestionRepository,
    IResetCodeRepository,
    IUserRepository,
)
from helpers.enums.user_role import UserRole
from helpers.exceptions.user_exceptions import (
    RelatedUserNotFoundException,
    UserNotFoundException,
    UserRoleConflictException,
)
from helpers.exceptions.question_exceptions import QuestionNotFoundException
from helpers.exceptions.activity_exceptions import ActivityNotFoundException
from models.activity import Activity
from models.admin import Admin
from models.associations import UserCodeAssociation
from models.doctor import Doctor
from models.patient import Patient
from models.question import Question
from models.user import User


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_email(self, email: str) -> Optional[UserDomain]:
        model: User | None = self.session.get(User, email)
        if model is None:
            return None
        return self._to_domain(model)

    def add(self, user: UserDomain) -> None:
        model = self._from_domain(user)
        self.session.add(model)

    def remove(self, user: UserDomain) -> None:
        model: User | None = self.session.get(User, user.email)
        if model is not None:
            self.session.delete(model)

    def update(self, user: UserDomain) -> None:
        model: User | None = self.session.get(User, user.email)
        if model is None:
            raise UserNotFoundException("Usuari no trobat.")
        self._apply_updates(user, model)

    def _to_domain(self, model: User) -> UserDomain:
        if self._role_count(model.email) != 1:
            raise UserRoleConflictException("L'usuari ha de tenir assignat exactament un únic rol.")
        role = model.role
        if role == UserRole.PATIENT and isinstance(model, Patient):
            return PatientDomain(
                email=model.email,
                password_hash=model.password,
                name=model.name,
                surname=model.surname,
                ailments=model.ailments,
                gender=model.gender,
                age=model.age,
                treatments=model.treatments,
                height_cm=model.height_cm,
                weight_kg=model.weight_kg,
                doctor_emails=[doctor.email for doctor in model.doctors],
            )
        if role == UserRole.DOCTOR and isinstance(model, Doctor):
            return DoctorDomain(
                email=model.email,
                password_hash=model.password,
                name=model.name,
                surname=model.surname,
                patient_emails=[patient.email for patient in model.patients],
            )
        if role == UserRole.ADMIN and isinstance(model, Admin):
            return AdminDomain(
                email=model.email,
                password_hash=model.password,
                name=model.name,
                surname=model.surname,
            )
        raise UserRoleConflictException("L'usuari ha de tenir assignat exactament un únic rol vàlid.")

    def _role_count(self, email: str) -> int:
        patient_exists = (
            self.session.query(Patient.email).filter(Patient.email == email).first()
            is not None
        )
        doctor_exists = (
            self.session.query(Doctor.email).filter(Doctor.email == email).first()
            is not None
        )
        admin_exists = (
            self.session.query(Admin.email).filter(Admin.email == email).first()
            is not None
        )
        return sum(int(flag) for flag in (patient_exists, doctor_exists, admin_exists))

    def _from_domain(self, user: UserDomain) -> User:
        if isinstance(user, PatientDomain):
            model = Patient(
                email=user.email,
                password=user.password_hash,
                name=user.name,
                surname=user.surname,
                role=UserRole.PATIENT,
                ailments=user.ailments,
                gender=user.gender,
                age=user.age,
                treatments=user.treatments,
                height_cm=user.height_cm,
                weight_kg=user.weight_kg,
            )
            model.doctors = self._fetch_doctors(user.doctor_emails)
            return model
        if isinstance(user, DoctorDomain):
            model = Doctor(
                email=user.email,
                password=user.password_hash,
                name=user.name,
                surname=user.surname,
                role=UserRole.DOCTOR,
            )
            model.patients = self._fetch_patients(user.patient_emails)
            return model
        if isinstance(user, AdminDomain):
            return Admin(
                email=user.email,
                password=user.password_hash,
                name=user.name,
                surname=user.surname,
                role=UserRole.ADMIN,
            )
        raise UserRoleConflictException("Rol d'usuari desconegut.")

    def _apply_updates(self, user: UserDomain, model: User) -> None:
        model.name = user.name
        model.surname = user.surname
        model.password = user.password_hash
        if isinstance(user, PatientDomain):
            if not isinstance(model, Patient):
                raise UserRoleConflictException("El rol d'usuari no correspon amb pacient.")
            model.ailments = user.ailments
            model.gender = user.gender
            model.age = user.age
            model.treatments = user.treatments
            model.height_cm = user.height_cm
            model.weight_kg = user.weight_kg
            model.doctors = self._fetch_doctors(user.doctor_emails)
        elif isinstance(user, DoctorDomain):
            if not isinstance(model, Doctor):
                raise UserRoleConflictException("El rol d'usuari no correspon amb metge.")
            model.patients = self._fetch_patients(user.patient_emails)
        elif isinstance(user, AdminDomain):
            if not isinstance(model, Admin):
                raise UserRoleConflictException("El rol d'usuari no correspon amb administrador.")
        else:
            raise UserRoleConflictException("Rol d'usuari desconegut.")

    def _fetch_doctors(self, emails: Iterable[str]) -> List[Doctor]:
        clean_emails = [e for e in emails if e]
        if not clean_emails:
            return []
        doctors: List[Doctor] = (
            self.session.query(Doctor)
            .filter(Doctor.email.in_(clean_emails))
            .all()
        )
        missing = set(clean_emails) - {d.email for d in doctors}
        if missing:
            raise RelatedUserNotFoundException(
                f"No s'ha trobat cap doctor amb el correu: {', '.join(missing)}"
            )
        return doctors

    def _fetch_patients(self, emails: Iterable[str]) -> List[Patient]:
        clean_emails = [e for e in emails if e]
        if not clean_emails:
            return []
        patients: List[Patient] = (
            self.session.query(Patient)
            .filter(Patient.email.in_(clean_emails))
            .all()
        )
        missing = set(clean_emails) - {p.email for p in patients}
        if missing:
            raise RelatedUserNotFoundException(
                f"No s'ha trobat cap pacient amb el correu: {', '.join(missing)}"
            )
        return patients


class SQLAlchemyPatientRepository(IPatientRepository):
    def __init__(self, session=None):
        self.session = session or db.session
        self.user_repo = SQLAlchemyUserRepository(self.session)

    def get_by_email(self, email: str) -> Optional[PatientDomain]:
        model: Patient | None = self.session.get(Patient, email)
        if model is None:
            return None
        return self.user_repo._to_domain(model)  # type: ignore[arg-type]

    def add(self, patient: PatientDomain) -> None:
        model = self.user_repo._from_domain(patient)
        self.session.add(model)

    def update(self, patient: PatientDomain) -> None:
        self.user_repo.update(patient)

    def fetch_by_emails(self, emails: Iterable[str]) -> List[PatientDomain]:
        clean_emails = [email for email in emails if email]
        if not clean_emails:
            return []
        patients: List[Patient] = (
            self.session.query(Patient)
            .filter(Patient.email.in_(clean_emails))
            .all()
        )
        missing = set(clean_emails) - {p.email for p in patients}
        if missing:
            raise RelatedUserNotFoundException(
                f"No s'ha trobat cap pacient amb el correu: {', '.join(missing)}"
            )
        return [self.user_repo._to_domain(patient) for patient in patients]  # type: ignore[list-item]


class SQLAlchemyDoctorRepository(IDoctorRepository):
    def __init__(self, session=None):
        self.session = session or db.session
        self.user_repo = SQLAlchemyUserRepository(self.session)

    def get_by_email(self, email: str) -> Optional[DoctorDomain]:
        model: Doctor | None = self.session.get(Doctor, email)
        if model is None:
            return None
        return self.user_repo._to_domain(model)  # type: ignore[arg-type]

    def add(self, doctor: DoctorDomain) -> None:
        model = self.user_repo._from_domain(doctor)
        self.session.add(model)

    def update(self, doctor: DoctorDomain) -> None:
        self.user_repo.update(doctor)

    def fetch_by_emails(self, emails: Iterable[str]) -> List[DoctorDomain]:
        clean_emails = [email for email in emails if email]
        if not clean_emails:
            return []
        doctors: List[Doctor] = (
            self.session.query(Doctor)
            .filter(Doctor.email.in_(clean_emails))
            .all()
        )
        missing = set(clean_emails) - {d.email for d in doctors}
        if missing:
            raise RelatedUserNotFoundException(
                f"No s'ha trobat cap doctor amb el correu: {', '.join(missing)}"
            )
        return [self.user_repo._to_domain(doctor) for doctor in doctors]  # type: ignore[list-item]


class SQLAlchemyAdminRepository(IAdminRepository):
    def __init__(self, session=None):
        self.session = session or db.session
        self.user_repo = SQLAlchemyUserRepository(self.session)

    def get_by_email(self, email: str) -> Optional[AdminDomain]:
        model: Admin | None = self.session.get(Admin, email)
        if model is None:
            return None
        return self.user_repo._to_domain(model)  # type: ignore[arg-type]

    def add(self, admin: AdminDomain) -> None:
        model = self.user_repo._from_domain(admin)
        self.session.add(model)

    def update(self, admin: AdminDomain) -> None:
        self.user_repo.update(admin)


class SQLAlchemyQuestionRepository(IQuestionRepository):
    def __init__(self, session=None):
        self.session = session or db.session

    def get(self, question_id: uuid.UUID) -> Optional[QuestionDomain]:
        model: Question | None = self.session.get(Question, question_id)
        if model is None:
            return None
        return self._to_domain(model)

    def list(self, filters: dict) -> List[QuestionDomain]:
        query = self.session.query(Question)
        question_id = filters.get("id")
        difficulty = filters.get("difficulty")
        difficulty_min = filters.get("difficulty_min")
        difficulty_max = filters.get("difficulty_max")
        question_type = filters.get("question_type")

        if question_id:
            query = query.filter(Question.id == question_id)
        if difficulty is not None:
            query = query.filter(Question.difficulty == difficulty)
        if difficulty_min is not None:
            query = query.filter(Question.difficulty >= difficulty_min)
        if difficulty_max is not None:
            query = query.filter(Question.difficulty <= difficulty_max)
        if question_type:
            query = query.filter(Question.question_type == question_type)

        return [self._to_domain(model) for model in query.all()]

    def add_many(self, questions: Iterable[QuestionDomain]) -> None:
        for question in questions:
            self.session.add(self._from_domain(question))

    def update(self, question: QuestionDomain) -> None:
        model: Question | None = self.session.get(Question, question.id)
        if model is None:
            raise QuestionNotFoundException("Pregunta no trobada.")
        model.text = question.text
        model.question_type = question.question_type
        model.difficulty = question.difficulty

    def remove(self, question: QuestionDomain) -> None:
        model: Question | None = self.session.get(Question, question.id)
        if model is not None:
            self.session.delete(model)

    def _to_domain(self, model: Question) -> QuestionDomain:
        return QuestionDomain(
            id=model.id,
            text=model.text,
            question_type=model.question_type,
            difficulty=model.difficulty,
        )

    def _from_domain(self, question: QuestionDomain) -> Question:
        return Question(
            id=question.id,
            text=question.text,
            question_type=question.question_type,
            difficulty=question.difficulty,
        )


class SQLAlchemyActivityRepository(IActivityRepository):
    def __init__(self, session=None):
        self.session = session or db.session

    def get(self, activity_id: uuid.UUID) -> Optional[ActivityDomain]:
        model: Activity | None = self.session.get(Activity, activity_id)
        if model is None:
            return None
        return self._to_domain(model)

    def list(self, filters: dict) -> List[ActivityDomain]:
        query = self.session.query(Activity)
        activity_id = filters.get("id")
        activity_title = filters.get("title")
        difficulty = filters.get("difficulty")
        difficulty_min = filters.get("difficulty_min")
        difficulty_max = filters.get("difficulty_max")
        activity_type = filters.get("activity_type")

        if activity_id:
            query = query.filter(Activity.id == activity_id)
        if activity_title is not None:
            query = query.filter(Activity.title == activity_title)
        if difficulty is not None:
            query = query.filter(Activity.difficulty == difficulty)
        if difficulty_min is not None:
            query = query.filter(Activity.difficulty >= difficulty_min)
        if difficulty_max is not None:
            query = query.filter(Activity.difficulty <= difficulty_max)
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)

        return [self._to_domain(model) for model in query.all()]

    def add_many(self, activities: Iterable[ActivityDomain]) -> None:
        for activity in activities:
            self.session.add(self._from_domain(activity))

    def update(self, activity: ActivityDomain) -> None:
        model: Activity | None = self.session.get(Activity, activity.id)
        if model is None:
            raise ActivityNotFoundException("Activitat no trobada.")
        model.title = activity.title
        model.description = activity.description
        model.activity_type = activity.activity_type
        model.difficulty = activity.difficulty

    def remove(self, activity: ActivityDomain) -> None:
        model: Activity | None = self.session.get(Activity, activity.id)
        if model is not None:
            self.session.delete(model)

    def _to_domain(self, model: Activity) -> ActivityDomain:
        return ActivityDomain(
            id=model.id,
            title=model.title,
            description=model.description,
            activity_type=model.activity_type,
            difficulty=model.difficulty,
        )

    def _from_domain(self, activity: ActivityDomain) -> Activity:
        return Activity(
            id=activity.id,
            title=activity.title,
            description=activity.description,
            activity_type=activity.activity_type,
            difficulty=activity.difficulty,
        )


class SQLAlchemyResetCodeRepository(IResetCodeRepository):
    def __init__(self, session=None):
        self.session = session or db.session

    def save_code(self, email: str, hashed_code: str, expiration: datetime) -> None:
        existing: UserCodeAssociation | None = self.session.get(
            UserCodeAssociation, email
        )
        if existing:
            self.session.delete(existing)
            self.session.flush()
        association = UserCodeAssociation(
            user_email=email,
            code=hashed_code,
            expiration=expiration,
        )
        self.session.add(association)

    def get_code(self, email: str) -> Optional[tuple[str, datetime]]:
        association: UserCodeAssociation | None = self.session.get(
            UserCodeAssociation, email
        )
        if association is None:
            return None
        return association.code, association.expiration

    def delete_code(self, email: str) -> None:
        association: UserCodeAssociation | None = self.session.get(
            UserCodeAssociation, email
        )
        if association:
            self.session.delete(association)
