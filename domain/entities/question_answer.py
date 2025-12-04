from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from .question import Question


@dataclass
class QuestionAnswer:
    """
    Domain representation of a question answered by a patient.  This acts as a
    simple data holder for the relationship between a question and the time at
    which it was answered.  It also carries any analysis metrics collected at
    answer time (e.g. from voice transcription).

    Attributes:
        question (Question): The underlying question that was answered.
        answered_at (datetime): When the answer occurred.  Should be timezone aware.
        analysis (Dict[str, float]): A flat dictionary of metric names to values.
    """

    question: Question
    answered_at: datetime
    analysis: Dict[str, float]

    def to_dict(self) -> dict:
        """Serialize the answered question for API responses.

        Returns:
            dict: A dictionary containing the question payload, the timestamp
                  and any analysis metrics.
        """
        return {
            "question": self.question.to_dict(),
            "answered_at": self.answered_at.isoformat(),
            "analysis": self.analysis,
        }
