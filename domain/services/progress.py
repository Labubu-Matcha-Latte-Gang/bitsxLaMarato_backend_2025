from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Tuple

from domain.entities.score import Score
from helpers.enums.question_types import QuestionType


class CompositeProgressStrategy(ABC):
    """
    Strategy interface for building a composite progress curve using the
    Inverse Efficiency Score (Townsend & Ashby, 1983), a cognitive psychology
    metric that merges accuracy and response time into a single efficiency
    value. Implementations must return a time-ordered series where higher
    values indicate better combined speed/accuracy performance across all
    `QuestionType` areas.
    """

    @abstractmethod
    def build_progress_series(self, scores: List[Score]) -> List[Tuple[datetime, float]]:
        """Return (timestamp, composite_score) pairs in ascending time order."""
        raise NotImplementedError


class InverseEfficiencyProgressStrategy(CompositeProgressStrategy):
    """
    Compute a patient-wide progress curve using the Inverse Efficiency Score
    (IES = reaction_time / accuracy). Each point blends activity score
    (accuracy proxy) and seconds to finish (reaction time). The series applies
    exponential smoothing per `QuestionType` and averages across all areas to
    highlight holistic improvement (lower IES -> higher efficiency).
    """

    MIN_ACCURACY = 0.05  # avoid division by zero; keeps denominator meaningful
    SMOOTHING_ALPHA = 0.35  # balance between recency and stability

    def build_progress_series(self, scores: List[Score]) -> List[Tuple[datetime, float]]:
        if not scores:
            return []

        ordered = sorted(scores, key=lambda s: s.completed_at)
        # Normalise reaction times to the patient's slowest sample to keep IES on a stable scale
        max_seconds = max((s.seconds_to_finish for s in ordered), default=0.0) or 1.0
        per_type_state: Dict[str, float] = {}
        series: List[Tuple[datetime, float]] = []

        for score in ordered:
            activity_type: QuestionType | None = getattr(score.activity, "activity_type", None)
            type_key = activity_type.value if activity_type else "unknown"

            accuracy = max(self.MIN_ACCURACY, min(score.score / 10.0, 1.0))
            normalised_time = max(0.0, score.seconds_to_finish) / max_seconds
            ies = normalised_time / accuracy
            efficiency = 1.0 / (1.0 + ies)

            previous = per_type_state.get(type_key)
            smoothed = efficiency if previous is None else previous + self.SMOOTHING_ALPHA * (efficiency - previous)
            per_type_state[type_key] = smoothed

            composite = sum(per_type_state.values()) / len(per_type_state)
            series.append((score.completed_at, composite))

        return series
