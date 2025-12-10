from db import db
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB


class TranscriptionSession(db.Model):
    """
    Database model representing an aggregated transcription session linked
    to a patient.  Each row stores cognitive analysis metrics derived
    from voice transcription for a specific session and patient.  These
    metrics are later consumed by recommendation strategies to adjust
    difficulty and content of activities and questions.

    Fields:
        id (int): Auto-incrementing primary key.
        patient_email (str): Foreign key referencing the patient's
            email.  Sessions are deleted when the patient is removed.
        metrics (JSONB): A JSON object containing arbitrary analysis
            metrics (floats).  See ``helpers.analysis_engine`` for
            possible keys.
        created_at (datetime): Timestamp when the session was created.
    """

    __tablename__ = "transcription_sessions"

    id = db.Column(db.Integer, primary_key=True)
    patient_email = db.Column(
        db.String(120),
        db.ForeignKey("patients.email", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metrics = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)