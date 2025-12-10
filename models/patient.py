from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped

from db import db
from helpers.enums.gender import Gender
from helpers.enums.user_role import UserRole
from models.associations import DoctorPatientAssociation, QuestionAnsweredAssociation
from models.user import User

if TYPE_CHECKING:
    from models.doctor import Doctor
    from models.question import Question


class Patient(User):
    __tablename__ = "patients"
    __allow_unmapped__ = True
    __table_args__ = (
        db.CheckConstraint("age >= 0 AND age <= 120", name="ck_patient_age_range"),
        db.CheckConstraint(
            "height_cm > 0 AND height_cm <= 250", name="ck_patient_height_range"
        ),
        db.CheckConstraint(
            "weight_kg > 0 AND weight_kg <= 600", name="ck_patient_weight_range"
        ),
    )

    email = db.Column(
        db.String(120),
        db.ForeignKey("users.email", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    ailments = db.Column(db.String(2048), nullable=True)
    gender = db.Column(db.Enum(Gender), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    treatments = db.Column(db.String(2048), nullable=True)
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)

    doctors: Mapped[list["Doctor"]] = db.relationship(
        "Doctor",
        secondary=DoctorPatientAssociation.__table__,
        back_populates="patients",
        lazy=True,
    )
    question_answers: Mapped[list[QuestionAnsweredAssociation]] = db.relationship(
        "QuestionAnsweredAssociation",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": UserRole.PATIENT,
    }

    def add_answered_questions(
        self,
        questions: set["Question"],
        answered_at: datetime | None = None,
        answer_text: str = "",
        analysis: dict | None = None,
    ) -> None:
        for question in questions:
            if question is None:
                continue
            existing = next(
                (qa for qa in self.question_answers if qa.question_id == question.id),
                None,
            )
            if existing:
                if answered_at:
                    existing.answered_at = answered_at
                if answer_text:
                    existing.answer_text = answer_text
                if analysis is not None:
                    existing.analysis = analysis
                continue
            self.question_answers.append(
                QuestionAnsweredAssociation(
                    question=question,
                    answered_at=answered_at or datetime.now(timezone.utc),
                    answer_text=answer_text or "",
                    analysis=analysis or {},
                )
            )

    def remove_answered_questions(self, questions: set["Question"]) -> None:
        for question in questions:
            if question is None:
                continue
            for association in list(self.question_answers):
                if association.question_id == question.id:
                    self.question_answers.remove(association)
                    break
