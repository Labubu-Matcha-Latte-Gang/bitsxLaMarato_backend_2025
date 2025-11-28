from datetime import datetime

import bcrypt
from db import db

class DoctorPatientAssociation(db.Model):
    __tablename__ = 'doctor_patient'

    doctor_email = db.Column(db.String(120), db.ForeignKey('doctors.email', onupdate='CASCADE'), primary_key=True)
    patient_email = db.Column(db.String(120), db.ForeignKey('patients.email', onupdate='CASCADE'), primary_key=True)

    def __repr__(self):
        return f"<DoctorPatientAssociation Doctor: {self.doctor_email}, Patient: {self.patient_email}>"
    
class UserCodeAssociation(db.Model):
    __tablename__ = 'user_codes'

    user_email = db.Column(db.String(120), db.ForeignKey('users.email', onupdate='CASCADE'), primary_key=True)
    code = db.Column(db.String(60), nullable=False)
    expiration = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<UserCodeAssociation User: {self.user_email}, Expiration: {self.expiration}>"
    
    def is_expired(self, current_time: datetime) -> bool:
        """
        Check if the code is expired.
        Args:
            current_time (datetime): The current time to compare with expiration.
        Returns:
            bool: True if the code is expired, False otherwise.
        """
        return current_time >= self.expiration
    
    def check_code(self, code: str) -> bool:
        """
        Check if the provided code matches the stored code.
        Args:
            code (str): The code to check.
        Returns:
            bool: True if the codes match, False otherwise.
        """
        return bcrypt.checkpw(code.encode('utf-8'), self.code.encode('utf-8'))