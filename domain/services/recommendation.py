from __future__ import annotations

"""
Recommendation strategies for tailoring activities and daily questions to
individual patients based on their historical performance and cognitive
metrics. These strategies can be injected into Patient methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from domain.entities.user import Patient
    from domain.repositories.interfaces import IScoreRepository, ITranscriptionAnalysisRepository
    from helpers.enums.question_types import QuestionType

class ActivityFilterStrategy(ABC):
    """
    Abstract base class defining the contract for activity filter strategies.
    """

    @abstractmethod
    def get_filters(
        self,
        patient: "Patient",
        score_repo: "IScoreRepository",
        transcription_repo: "ITranscriptionAnalysisRepository",
    ) -> Dict[str, float]:
        raise NotImplementedError()

class DailyQuestionFilterStrategy(ABC):
    """
    Abstract base class defining the contract for daily question filter
    strategies.
    """

    @abstractmethod
    def get_filters(
        self,
        patient: "Patient",
        score_repo: "IScoreRepository",
        transcription_repo: "ITranscriptionAnalysisRepository",
    ) -> Dict[str, float | "QuestionType"]:
        raise NotImplementedError()

class ScoreBasedActivityStrategy(ActivityFilterStrategy):
    """
    Default strategy for generating activity filters based on patient scores
    and cognitive analysis from voice transcriptions.

    Combines the average normalised score and a deterioration index from
    transcriptions. The final ability in [0,1] is scaled to difficulty
    [0,5], and a ±1 window is returned.
    """

    MAX_SCORE: float = 100.0
    SCORE_WEIGHT: float = 0.7

    def get_filters(
        self,
        patient: "Patient",
        score_repo: "IScoreRepository",
        transcription_repo: "ITranscriptionAnalysisRepository",
    ) -> Dict[str, float]:
        scores = score_repo.list_by_patient(patient.email)
        if scores:
            normalised_scores = [min(max(s.score / self.MAX_SCORE, 0.0), 1.0) for s in scores]
            avg_score = sum(normalised_scores) / len(normalised_scores)
        else:
            avg_score = 0.5

        sessions = transcription_repo.list_by_patient(patient.email)
        if sessions:
            deteriorations = [self._compute_deterioration(sess.metrics) for sess in sessions]
            avg_deterioration = min(max(sum(deteriorations) / len(deteriorations), 0.0), 1.0)
        else:
            avg_deterioration = 0.0

        ability = (
            self.SCORE_WEIGHT * avg_score +
            (1.0 - self.SCORE_WEIGHT) * (1.0 - avg_deterioration)
        )
        ability = min(max(ability, 0.0), 1.0)
        recommended_difficulty = ability * 5.0
        difficulty_min = max(0.0, recommended_difficulty - 1.0)
        difficulty_max = min(5.0, recommended_difficulty + 1.0)
        return {
            "difficulty_min": difficulty_min,
            "difficulty_max": difficulty_max,
        }

    def _compute_deterioration(self, metrics: Dict[str, float]) -> float:
        """
        Derive a scalar deterioration index from a metrics dictionary.
        """
        values: List[float] = []
        latency = metrics.get("raw_latency")
        if latency is not None:
            values.append(min(max(latency / 10.0, 0.0), 1.0))
        idea_density = metrics.get("idea_density")
        if idea_density is not None:
            normalized = max(0.0, 1.0 - min(idea_density / 5.0, 1.0))
            values.append(normalized)
        if not values:
            return 0.0
        return sum(values) / len(values)

class ScoreBasedQuestionStrategy(DailyQuestionFilterStrategy):
    """
    Default strategy for generating daily question filters leveraging past
    scores and cognitive metrics. Computes a difficulty range as above and
    selects a QuestionType where the patient performs worst, adjusting for
    lexical or processing impairments.
    """

    MAX_SCORE: float = 100.0
    SCORE_WEIGHT: float = 0.7

    def get_filters(
        self,
        patient: "Patient",
        score_repo: "IScoreRepository",
        transcription_repo: "ITranscriptionAnalysisRepository",
    ) -> Dict[str, float | "QuestionType"]:
        # Difficulty range (reuses the activity strategy)
        activity_strategy = ScoreBasedActivityStrategy()
        difficulty_filters = activity_strategy.get_filters(patient, score_repo, transcription_repo)

        # Scores grouped by QuestionType
        scores = score_repo.list_by_patient(patient.email)
        from helpers.enums.question_types import QuestionType
        score_sums: Dict[QuestionType, float] = {qt: 0.0 for qt in QuestionType}
        score_counts: Dict[QuestionType, int] = {qt: 0 for qt in QuestionType}
        for s in scores:
            qt = getattr(s.activity, "activity_type", None)
            if qt is None:
                continue
            score_sums[qt] += min(max(s.score / self.MAX_SCORE, 0.0), 1.0)
            score_counts[qt] += 1
        weights: Dict[QuestionType, float] = {}
        for qt in QuestionType:
            if score_counts[qt] > 0:
                mean_score = score_sums[qt] / score_counts[qt]
            else:
                mean_score = 0.0  # unexplored area
            weights[qt] = 1.0 - mean_score

        # Deterioration adjustments
        sessions = transcription_repo.list_by_patient(patient.email)
        lexical_impairment = 0.0
        processing_impairment = 0.0
        if sessions:
            lex_vals: List[float] = []
            proc_vals: List[float] = []
            for sess in sessions:
                metrics = sess.metrics
                id_val = metrics.get("idea_density")
                if id_val is not None:
                    lex_vals.append(max(0.0, 1.0 - min(id_val / 5.0, 1.0)))
                pn_val = metrics.get("p_n_ratio")
                if pn_val is not None:
                    lex_vals.append(max(0.0, 1.0 - min(pn_val / 5.0, 1.0)))
                lat = metrics.get("raw_latency")
                if lat is not None:
                    proc_vals.append(min(max(lat / 10.0, 0.0), 1.0))
                pause = metrics.get("pause_time")
                if pause is not None:
                    proc_vals.append(min(max(pause / 10.0, 0.0), 1.0))
            if lex_vals:
                lexical_impairment = sum(lex_vals) / len(lex_vals)
            if proc_vals:
                processing_impairment = sum(proc_vals) / len(proc_vals)

        adjusted_weights: Dict[QuestionType, float] = defaultdict(float)
        for qt in QuestionType:
            adjusted_weights[qt] = weights.get(qt, 0.0)

        if lexical_impairment >= processing_impairment:
            from helpers.enums.question_types import QuestionType as QT
            adjusted_weights[QT.WORDS] += lexical_impairment
        else:
            from helpers.enums.question_types import QuestionType as QT
            adjusted_weights[QT.SPEED] += processing_impairment

        if all(w <= 0.0 for w in adjusted_weights.values()):
            # No preference if no data
            return difficulty_filters

        selected_type = max(adjusted_weights, key=adjusted_weights.get)
        difficulty_filters["question_type"] = selected_type
        return difficulty_filters
