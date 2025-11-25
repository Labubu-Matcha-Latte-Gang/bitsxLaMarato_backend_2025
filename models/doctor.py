from db import db

from helpers.enums.user_role import UserRole
from models.associations import DoctorPatientAssociation
from models.interfaces import IUserRole

class Doctor(db.Model, IUserRole):
    __tablename__ = 'doctors'

    email = db.Column(db.String(120), db.ForeignKey('users.email', onupdate='CASCADE'), primary_key=True)
    user = db.relationship('User', back_populates='doctor', uselist=False)
    patients: list = db.relationship(
        'Patient',
        secondary=DoctorPatientAssociation.__table__,
        back_populates='doctors',
        lazy=True,
    )

    def add_patients(self, patients: set, sync_with_patient: bool = True) -> None:
        """
        Add patients to this doctor if not already present
        Args:
            patients (set[Patient]): The patients to add
            sync_with_patient (bool): Whether to update the patient side as well
        """
        for patient in patients:
            if patient is None:
                continue
            if patient not in self.patients:
                self.patients.append(patient)
            if sync_with_patient and self not in patient.doctors:
                patient.add_doctors({self}, sync_with_doctor=False)

    def remove_patients(self, patients: set, sync_with_patient: bool = True) -> None:
        """
        Remove patients from this doctor if present
        Args:
            patients (set[Patient]): The patients to remove
            sync_with_patient (bool): Whether to update the patient side as well
        """
        for patient in patients:
            if patient is None:
                continue
            if patient in self.patients:
                self.patients.remove(patient)
            if sync_with_patient and self in patient.doctors:
                patient.remove_doctors({self}, sync_with_doctor=False)

    def remove_all_patients(self) -> None:
        """
        Remove all patients from this doctor
        """
        for patient in list(self.patients):
            self.remove_patients({patient})

    def remove_all_associations(self) -> None:
        """
        Remove all associations with patients
        """
        self.remove_all_patients()

    def get_user(self):
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
    
    def get_email(self) -> str:
        """
        Get the doctor's email
        Returns:
            str: The doctor's email
        """
        return self.email
    
    def set_email(self, new_email: str) -> None:
        """
        Set a new email for the doctor
        Args:
            new_email (str): The new email to set
        """
        user = self.get_user()
        user.set_email(new_email)

    def to_dict(self) -> dict:
        """
        Convert the Doctor object to a dictionary
        Returns:
            dict: A dictionary representation of the Doctor object
        """
        return {
            "patients": [patient.get_email() for patient in self.patients]
        }
    
    def get_role(self) -> UserRole:
        """
        Get the role of this user
        Returns:
            UserRole: The role of this user
        """
        return UserRole.DOCTOR

    def set_properties(self, data: dict) -> None:
        """
        Set multiple properties of the doctor from a dictionary
        Args:
            data (dict): A dictionary containing the properties to set
        """
        if 'patients' in data:
            new_patients = data.get('patients') or {}
            self.add_patients(new_patients)
    
    def doctor_of_this_patient(self, patient) -> bool:
        """
        Check if this doctor is associated with the given patient.
        """
        return patient in self.patients
