"""
Recommendation strategies for tailoring activities and daily questions to
individual patients based on their historical performance and cognitive
metrics. These strategies can be injected into Patient methods.
"""
from __future__ import annotations

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

    MAX_SCORE: float = 10.0
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
    Default strategy for generating daily question filters based primarily on
    cognitive analysis metrics.

    Unlike activities, daily questions are not scored by the patient.
    Consequently, this strategy does **not** attempt to infer category
    weights from past performance. Instead, it uses the patient’s
    transcription-derived metrics to decide both the difficulty range and
    the question type:
      1. Difficulty range: reuse the activity recommendation logic to
         compute a difficulty window. The patient’s scores on activities
         still serve as a proxy for overall ability.
      2. Impairment detection: aggregate two measures from the
         transcription sessions: lexical impairment and processing
         impairment. Each metric is normalised to [0,1] and averaged.
      3. Question type selection: choose an appropriate `QuestionType`
         based on these impairments. If lexical impairment dominates by
         >0.1, `WORDS` is recommended; if processing impairment dominates,
         `SPEED`; otherwise the average impairment is mapped to
         `CONCENTRATION`, `SORTING` or `MULTITASKING`.
    When no transcription data are available, the strategy returns only a
    difficulty range without specifying `question_type`.
    """

    MAX_SCORE: float = 10.0
    SCORE_WEIGHT: float = 0.0

    def get_filters(
        self,
        patient: "Patient",
        score_repo: "IScoreRepository",
        transcription_repo: "ITranscriptionAnalysisRepository",
    ) -> Dict[str, float | "QuestionType"]:
        activity_strategy = ScoreBasedActivityStrategy()
        difficulty_filters = activity_strategy.get_filters(
            patient, score_repo, transcription_repo
        )

        sessions = transcription_repo.list_by_patient(patient.email)
        if not sessions:
            return difficulty_filters

        lexical_vals: List[float] = []
        processing_vals: List[float] = []
        for sess in sessions:
            metrics = sess.metrics
            id_val = metrics.get("idea_density")
            if id_val is not None:
                lexical_vals.append(max(0.0, 1.0 - min(id_val / 5.0, 1.0)))
            pn_val = metrics.get("p_n_ratio")
            if pn_val is not None:
                lexical_vals.append(max(0.0, 1.0 - min(pn_val / 5.0, 1.0)))
            lat = metrics.get("raw_latency")
            if lat is not None:
                processing_vals.append(min(max(lat / 10.0, 0.0), 1.0))
            pause = metrics.get("pause_time")
            if pause is not None:
                processing_vals.append(min(max(pause / 10.0, 0.0), 1.0))

        lexical_impairment = sum(lexical_vals) / len(lexical_vals) if lexical_vals else 0.0
        processing_impairment = sum(processing_vals) / len(processing_vals) if processing_vals else 0.0

        from helpers.enums.question_types import QuestionType
        if lexical_impairment - processing_impairment > 0.1:
            selected_type = QuestionType.WORDS
        elif processing_impairment - lexical_impairment > 0.1:
            selected_type = QuestionType.SPEED
        else:
            overall = (lexical_impairment + processing_impairment) / 2.0
            if overall >= 0.66:
                selected_type = QuestionType.CONCENTRATION
            elif overall >= 0.33:
                selected_type = QuestionType.SORTING
            else:
                selected_type = QuestionType.MULTITASKING

        difficulty_filters["question_type"] = selected_type
        return difficulty_filters
