from db import db

from models.user import User
from models.associations import DoctorPatientAssociation

class Doctor(db.Model):
    __tablename__ = 'doctors'

    email = db.Column(db.String(120), db.ForeignKey('users.email'), primary_key=True)
    user: User = db.relationship('User', back_populates='doctor', uselist=False)
    patients: list = db.relationship(
        'Patient',
        secondary=DoctorPatientAssociation.__table__,
        back_populates='doctors',
        lazy=True,
    )

    def get_user(self) -> User:
        """
        Get the associated User object
        Returns:
            User: The associated User object
        """
        return self.user

    def get_patients(self) -> list:
        """
        Get the doctor's patients
        Returns:
            list: The doctor's patients
        """
        return self.patients