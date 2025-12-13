from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID, JSONB

import bcrypt
from db import db

class DoctorPatientAssociation(db.Model):
    __tablename__ = 'doctor_patient'

    doctor_email = db.Column(
        db.String(120),
        db.ForeignKey('doctors.email', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    patient_email = db.Column(
        db.String(120),
        db.ForeignKey('patients.email', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )

    def __repr__(self):
        return f"<DoctorPatientAssociation Doctor: {self.doctor_email}, Patient: {self.patient_email}>"
    
class UserCodeAssociation(db.Model):
    __tablename__ = 'user_codes'

    user_email = db.Column(
        db.String(120),
        db.ForeignKey('users.email', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
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
        expiration = self.expiration
        # Ensure both datetimes are timezone-aware and in UTC
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        return current_time >= expiration
    
    def check_code(self, code: str) -> bool:
        """
        Check if the provided code matches the stored code.
        Args:
            code (str): The code to check.
        Returns:
            bool: True if the codes match, False otherwise.
        """
        return bcrypt.checkpw(code.encode('utf-8'), self.code.encode('utf-8'))
    
class QuestionAnsweredAssociation(db.Model):
    __tablename__ = 'questions_answered'

    patient_email = db.Column(
        db.String(120),
        db.ForeignKey('patients.email', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    question_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('questions.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    answered_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), primary_key=True)
    answer_text = db.Column(db.Text, nullable=False, default="")
    analysis = db.Column(JSONB, nullable=False, default=dict)
    question = db.relationship('Question', lazy=True)
    patient = db.relationship('Patient', back_populates='question_answers', lazy=True)

    def to_dict(self) -> dict:
        """
        Convert the question to a serializable dictionary.
        Returns:
            dict: A dictionary representation of the question.
        """
        return {
            "question": {
                "id": str(self.question.id),
                "text": self.question.text,
                "question_type": self.question.question_type.value if self.question.question_type else None,
                "difficulty": self.question.difficulty,
            },
            "answered_at": self.answered_at.isoformat(),
            "analysis": self.analysis,
            "answer_text": self.answer_text,
        }

    def __repr__(self):
        return (
            f"<QuestionAnsweredAssociation Patient: {self.patient_email}, "
            f"Question ID: {self.question_id}, Answered At: {self.answered_at}, "
            f"Answer: {self.answer_text or ''}>"
        )
