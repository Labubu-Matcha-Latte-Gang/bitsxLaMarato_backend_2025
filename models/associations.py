from db import db

class DoctorPatientAssociation(db.Model):
    __tablename__ = 'doctor_patient'

    doctor_email = db.Column(db.String(120), db.ForeignKey('doctors.email', onupdate='CASCADE'), primary_key=True)
    patient_email = db.Column(db.String(120), db.ForeignKey('patients.email', onupdate='CASCADE'), primary_key=True)

    def __repr__(self):
        return f"<DoctorPatientAssociation Doctor: {self.doctor_email}, Patient: {self.patient_email}>"