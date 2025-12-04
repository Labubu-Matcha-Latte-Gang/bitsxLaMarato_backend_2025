from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.entities.activity import Activity
from domain.entities.user import Patient


@dataclass
class Score:
    patient: Patient
    activity: Activity
    completed_at: datetime
    score: float
    seconds_to_finish: float

    def to_dict(self) -> dict:
        """
        Serialize the score to a dictionary.
        Returns:
            dict: Public representation of the score.
        """
        return {
            "patient": self.patient.to_dict(),
            "activity": self.activity.to_dict(),
            "completed_at": self.completed_at.isoformat(),
            "score": self.score,
            "seconds_to_finish": self.seconds_to_finish,
        }