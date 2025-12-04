from __future__ import annotations

from datetime import datetime, timezone

from domain.entities.activity import Activity
from domain.entities.score import Score
from domain.entities.user import Patient
from domain.repositories import IActivityRepository, IScoreRepository
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.activity_exceptions import ActivityNotFoundException


class ScoreService:
    """
    Application service to manage activity completion scores.
    """

    def __init__(
        self,
        score_repo: IScoreRepository,
        activity_repo: IActivityRepository,
        uow: IUnitOfWork,
    ) -> None:
        self.score_repo = score_repo
        self.activity_repo = activity_repo
        self.uow = uow

    def complete_activity(
        self,
        patient: Patient,
        activity: Activity,
        score_value: float,
        seconds_to_finish: float,
    ) -> Score:
        """
        Register a completed activity for the given patient.
        """
        score = Score(
            patient=patient,
            activity=activity,
            completed_at=datetime.now(timezone.utc),
            score=score_value,
            seconds_to_finish=seconds_to_finish,
        )

        with self.uow:
            self.score_repo.add(score)
            self.uow.commit()

        return score
