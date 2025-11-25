from db import db

from models.associations import DoctorPatientAssociation
from helpers.enums.gender import Gender

class Patient(db.Model):
    __tablename__ = 'patients'

    email = db.Column(db.String(120), db.ForeignKey('users.email', onupdate='CASCADE'), primary_key=True)
    ailments = db.Column(db.String(1024), nullable=True)
    gender = db.Column(db.Enum(Gender), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', back_populates='patient', uselist=False)
    doctors: list = db.relationship(
        'Doctor',
        secondary=DoctorPatientAssociation.__table__,
        back_populates='patients',
        lazy=True,
    )

    def add_doctor(self, doctor) -> None:
        """
        Add a doctor to this patient if not already present
        Args:
            doctor (Doctor): The doctor to add
        """
        if doctor not in self.doctors:
            self.doctors.append(doctor)

    def remove_doctor(self, doctor) -> None:
        """
        Remove a doctor from this patient if present
        Args:
            doctor (Doctor): The doctor to remove
        """
        if doctor in self.doctors:
            self.doctors.remove(doctor)

    def remove_all_doctors(self) -> None:
        """
        Remove all doctors from this patient
        """
        self.doctors.clear()

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