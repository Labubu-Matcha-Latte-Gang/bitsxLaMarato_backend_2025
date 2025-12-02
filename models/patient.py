from __future__ import annotations
from datetime import datetime, timezone

from db import db
from sqlalchemy.orm import Mapped
from typing import TYPE_CHECKING

from helpers.enums.user_role import UserRole
from models.associations import DoctorPatientAssociation, QuestionAnsweredAssociation
from helpers.enums.gender import Gender
from models.interfaces import IUserRole

if TYPE_CHECKING:
    from models.doctor import Doctor
    from models.question import Question

class Patient(db.Model, IUserRole):
    __tablename__ = 'patients'
    __allow_unmapped__ = True

    email = db.Column(db.String(120), db.ForeignKey('users.email', onupdate='CASCADE'), primary_key=True)
    ailments = db.Column(db.String(2048), nullable=True)
    gender = db.Column(db.Enum(Gender), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    treatments = db.Column(db.String(2048), nullable=True)
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    user = db.relationship('User', back_populates='patient', uselist=False)
    doctors: Mapped[list['Doctor']] = db.relationship(
        'Doctor',
        secondary=DoctorPatientAssociation.__table__,
        back_populates='patients',
        lazy=True,
    )
    question_answers: Mapped[list[QuestionAnsweredAssociation]] = db.relationship(
        'QuestionAnsweredAssociation',
        back_populates='patient',
        cascade='all, delete-orphan',
        lazy=True,
    )

    def add_doctors(self, doctors:set, sync_with_doctor: bool = True) -> None:
        """
        Add doctors to this patient if not already present
        Args:
            doctors (set[Doctor]): The doctors to add
            sync_with_doctor (bool): Whether to update the doctor side as well
        """
        for doctor in doctors:
            if doctor is None:
                continue
            if doctor not in self.doctors:
                self.doctors.append(doctor)
            if sync_with_doctor and self not in doctor.patients:
                doctor.add_patients({self}, sync_with_patient=False)

    def remove_doctors(self, doctors:set, sync_with_doctor: bool = True) -> None:
        """
        Remove doctors from this patient if present
        Args:
            doctors (set[Doctor]): The doctor to remove
            sync_with_doctor (bool): Whether to update the doctor side as well
        """
        for doctor in doctors:
            if doctor is None:
                continue
            if doctor in self.doctors:
                self.doctors.remove(doctor)
            if sync_with_doctor and self in doctor.patients:
                doctor.remove_patients({self}, sync_with_patient=False)

    def remove_all_doctors(self) -> None:
        """
        Remove all doctors from this patient
        """
        for doctor in list(self.doctors):
            self.remove_doctors({doctor})

    def remove_all_associations_between_user_roles(self) -> None:
        """
        Remove all associations with doctors.
        """
        self.remove_all_doctors()

    def add_answered_questions(self, questions:set['Question'], answered_at: datetime | None = None) -> None:
        """
        Add questions to the answered list if not already present.
        Args:
            questions (set[Question]): Questions to mark as answered.
            answered_at (datetime | None): Timestamp to store; defaults to now UTC.
        """
        for question in questions:
            if question is None:
                continue
            existing = next((qa for qa in self.question_answers if qa.question_id == question.id), None)
            if existing:
                if answered_at:
                    existing.answered_at = answered_at
                continue
            self.question_answers.append(
                QuestionAnsweredAssociation(
                    question=question,
                    answered_at=answered_at or datetime.now(timezone.utc),
                )
            )

    def remove_answered_questions(self, questions:set['Question']) -> None:
        """
        Remove answered question associations for the given questions.
        Args:
            questions (set[Question]): Questions to unmark as answered.
        """
        for question in questions:
            if question is None:
                continue
            for association in list(self.question_answers):
                if association.question_id == question.id:
                    self.question_answers.remove(association)
                    break

    def get_answered_questions(self) -> list[QuestionAnsweredAssociation]:
        """
        Get associations of answered questions.
        Returns:
            list[QuestionAnsweredAssociation]: Associations for answered questions.
        """
        return self.question_answers

    def has_answered_question(self, question: 'Question') -> bool:
        """
        Check if the patient answered a given question.
        Args:
            question (Question): Question to check.
        Returns:
            bool: True if answered, False otherwise.
        """
        return any(qa.question_id == question.id for qa in self.question_answers)

    def remove_all_answered_questions(self) -> None:
        """
        Remove all answered question associations.
        """
        self.question_answers.clear()

    def get_user(self):
        """
        Get the associated User object
        Returns:
            User: The associated User object
        """
        return self.user

    def get_ailments(self) -> str | None:
        """
        Get the patient's ailments
        Returns:
            str | None: The patient's ailments
        """
        return self.ailments
    
    def get_doctors(self) -> list:
        """
        Get the patient's doctors
        Returns:
            list: The patient's doctors
        """
        return self.doctors
    
    def get_email(self) -> str:
        """
        Get the patient's email
        Returns:
            str: The patient's email
        """
        return self.email
    
    def set_email(self, new_email: str) -> None:
        """
        Set a new email for the patient
        Args:
            new_email (str): The new email to set
        """
        user = self.get_user()
        user.set_email(new_email)

    def set_ailments(self, new_ailments: str | None) -> None:
        """
        Set new ailments for the patient
        Args:
            new_ailments (str | None): The new ailments to set
        """
        self.ailments = new_ailments

    def get_gender(self) -> Gender:
        """
        Get the patient's gender
        Returns:
            Gender: The patient's gender
        """
        return self.gender
    
    def set_gender(self, new_gender: Gender) -> None:
        """
        Set a new gender for the patient
        Args:
            new_gender (Gender): The new gender to set
        """
        self.gender = new_gender

    def get_age(self) -> int:
        """
        Get the patient's age
        Returns:
            int: The patient's age
        """
        return self.age
    
    def set_age(self, new_age: int) -> None:
        """
        Set a new age for the patient
        Args:
            new_age (int): The new age to set
        """
        self.age = new_age

    def get_treatments(self) -> str | None:
        """
        Get the patient's treatments
        Returns:
            str | None: The patient's treatments
        """
        return self.treatments
    
    def set_treatments(self, new_treatments: str | None) -> None:
        """
        Set new treatments for the patient
        Args:
            new_treatments (str | None): The new treatments to set
        """
        self.treatments = new_treatments

    def get_height_cm(self) -> float | None:
        """
        Get the patient's height in centimeters
        Returns:
            float | None: The patient's height in centimeters
        """
        return self.height_cm
    
    def set_height_cm(self, new_height_cm: float | None) -> None:
        """
        Set a new height in centimeters for the patient
        Args:
            new_height_cm (float | None): The new height in centimeters to set
        """
        self.height_cm = new_height_cm

    def get_weight_kg(self) -> float | None:
        """
        Get the patient's weight in kilograms
        Returns:
            float | None: The patient's weight in kilograms
        """
        return self.weight_kg
    
    def set_weight_kg(self, new_weight_kg: float | None) -> None:
        """
        Set a new weight in kilograms for the patient
        Args:
            new_weight_kg (float | None): The new weight in kilograms to set
        """
        self.weight_kg = new_weight_kg

    def to_dict(self) -> dict:
        """
        Convert the Patient object to a dictionary
        Returns:
            dict: A dictionary representation of the Patient object
        """
        return {
            "ailments": self.ailments,
            "gender": self.gender.value if self.gender else None,
            "age": self.age,
            "treatments": self.treatments,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "doctors": [doctor.get_email() for doctor in self.doctors]
        }
    
    def get_role(self) -> UserRole:
        """
        Get the role of this user
        Returns:
            UserRole: The role of this user
        """
        return UserRole.PATIENT

    def set_properties(self, data: dict) -> None:
        """
        Set multiple properties of the patient from a dictionary
        Args:
            data (dict): A dictionary containing the properties to set
        """
        if 'ailments' in data:
            self.set_ailments(data['ailments'])
        if 'gender' in data:
            self.set_gender(data['gender'])
        if 'age' in data:
            self.set_age(data['age'])
        if 'treatments' in data:
            self.set_treatments(data['treatments'])
        if 'height_cm' in data:
            self.set_height_cm(data['height_cm'])
        if 'weight_kg' in data:
            self.set_weight_kg(data['weight_kg'])
        if 'doctors' in data:
            new_doctors = data.get('doctors') or {}
            self.add_doctors(new_doctors)

    def doctor_of_this_patient(self, patient) -> bool:
        """
        Patients do not manage other patients.
        """
        return False

    def get_daily_question_filters(self) -> dict:
        """
        Get filters for daily question selection based on patient attributes.
        Returns:
            dict: A dictionary of filters for daily question selection.
        """
        # TODO: Implement logic to derive filters based on patient attributes
        return {}
    
    def get_recommended_activity_filters(self) -> dict:
        """
        Get filters for recommended activity selection based on patient attributes.
        Returns:
            dict: A dictionary of filters for recommended activity selection.
        """
        # TODO: Implement logic to derive filters based on patient attributes
        return {}
