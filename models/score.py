from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from db import db


class Score(db.Model):
    __tablename__ = 'scores'
    __allow_unmapped__ = True
    __table_args__ = (
        db.CheckConstraint(
            'score >= 0 AND score <= 10',
            name='check_score_range',
        ),
        db.CheckConstraint(
            'seconds_to_finish >= 0',
            name='non_negative_seconds_to_finish',
        ),
    )

    patient_email = db.Column(db.String(120), db.ForeignKey('patients.email', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    activity_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('activities.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    completed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), primary_key=True)
    score = db.Column(db.Float, nullable=False)
    seconds_to_finish = db.Column(db.Float, nullable=False, default=0.0)
    activity = db.relationship('Activity', lazy=True)
    patient = db.relationship('Patient', lazy=True)
