from db import db

from helpers.enums.user_role import UserRole
from models.associations import DoctorPatientAssociation
from helpers.enums.gender import Gender

class Patient(db.Model):
    __tablename__ = 'patients'

    email = db.Column(db.String(120), db.ForeignKey('users.email', onupdate='CASCADE'), primary_key=True)
    ailments = db.Column(db.String(2048), nullable=True)
    gender = db.Column(db.Enum(Gender), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    treatments = db.Column(db.String(2048), nullable=True)
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    user = db.relationship('User', back_populates='patient', uselist=False)
    doctors: list = db.relationship(
        'Doctor',
        secondary=DoctorPatientAssociation.__table__,
        back_populates='patients',
        lazy=True,
    )

    def add_doctors(self, doctors:set) -> None:
        """
        Add doctors to this patient if not already present
        Args:
            doctors (set[Doctor]): The doctors to add
        """
        for doctor in doctors:
            if doctor is not None and doctor not in self.doctors:
                self.doctors.append(doctor)

    def remove_doctors(self, doctors:set) -> None:
        """
        Remove doctors from this patient if present
        Args:
            doctors (set[Doctor]): The doctor to remove
        """
        for doctor in doctors:
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
            "gender": self.gender,
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