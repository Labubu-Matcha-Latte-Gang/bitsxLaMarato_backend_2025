from db import db

from models.user import User
from models.associations import DoctorPatientAssociation

class Patient(db.Model):
    __tablename__ = 'patients'

    email = db.Column(db.String(120), db.ForeignKey('users.email'), primary_key=True)
    ailments = db.Column(db.String(1024), nullable=True)
    user: User = db.relationship('User', back_populates='patient', uselist=False)
    doctors: list = db.relationship(
        'Doctor',
        secondary=DoctorPatientAssociation.__table__,
        back_populates='patients',
        lazy=True,
    )

    def get_user(self) -> User:
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