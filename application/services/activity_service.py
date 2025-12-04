from __future__ import annotations

import uuid
from random import choice
from typing import List

from domain.entities.activity import Activity
from domain.entities.user import Patient
from domain.repositories import IActivityRepository
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.activity_exceptions import (
    ActivityCreationException,
    ActivityNotFoundException,
    ActivityUpdateException,
)


class ActivityService:
    def __init__(self, activity_repo: IActivityRepository, uow: IUnitOfWork):
        self.activity_repo = activity_repo
        self.uow = uow

    def create_activities(self, payloads: List[dict]) -> List[Activity]:
        try:
            activities = [
                Activity(
                    id=uuid.uuid4(),
                    title=payload["title"],
                    description=payload["description"],
                    activity_type=payload["activity_type"],
                    difficulty=payload["difficulty"],
                )
                for payload in payloads
            ]
            with self.uow:
                self.activity_repo.add_many(activities)
                self.uow.commit()
            return activities
        except Exception as exc:
            raise ActivityCreationException(
                f"No s'han pogut crear les activitats: {str(exc)}"
            ) from exc

    def get_activity(self, activity_id: uuid.UUID) -> Activity:
        activity = self.activity_repo.get(activity_id)
        if not activity:
            raise ActivityNotFoundException(
                f"No s'ha trobat cap activitat amb l'ID {activity_id}."
            )
        return activity
    
    def list_activities(self, filters: dict) -> List[Activity]:
        activities = self.activity_repo.list(filters)
        if filters.get("id") and not activities:
            raise ActivityNotFoundException(
                f"No s'ha trobat cap activitat amb l'ID {filters.get('id')}."
            )
        return activities

    def update_activity(self, activity_id: uuid.UUID, update_data: dict) -> Activity:
        activity = self.activity_repo.get(activity_id)
        if not activity:
            raise ActivityNotFoundException(
                f"No s'ha trobat cap activitat amb l'ID {activity_id}."
            )
        try:
            activity.set_properties(update_data)
            with self.uow:
                self.activity_repo.update(activity)
                self.uow.commit()
            return activity
        except Exception as exc:
            raise ActivityUpdateException(
                f"No s'ha pogut actualitzar l'activitat: {str(exc)}"
            ) from exc

    def delete_activity(self, activity_id: uuid.UUID) -> None:
        activity = self.activity_repo.get(activity_id)
        if not activity:
            raise ActivityNotFoundException(
                f"No s'ha trobat cap activitat amb l'ID {activity_id}."
            )
        with self.uow:
            self.activity_repo.remove(activity)
            self.uow.commit()

    def get_recommended(self, patient: Patient) -> Activity:
        filters = patient.get_recommended_activity_filters()
        activities = self.activity_repo.list(filters)
        if not activities:
            activities = self.activity_repo.list({})
        if not activities:
            raise ActivityNotFoundException(
                "No hi ha activitats disponibles a la base de dades."
            )
        return choice(activities)
