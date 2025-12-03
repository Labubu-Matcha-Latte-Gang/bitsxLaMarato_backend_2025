from __future__ import annotations
from abc import ABC, abstractmethod
import uuid
from random import choice

from db import db
from helpers.exceptions.activity_exceptions import (
    ActivityCreationException,
    ActivityNotFoundException,
    ActivityUpdateException,
)
from models.activity import Activity
from models.patient import Patient


class IActivityController(ABC):
    """
    Interface for Activity Controller.
    """
    __instance: 'IActivityController' = None

    @abstractmethod
    def get_activity(self, activity_id: uuid.UUID) -> Activity:
        """
        Retrieve an activity by its ID.
        Args:
            activity_id (uuid.UUID): The ID of the activity to retrieve.
        Returns:
            Activity: The activity object corresponding to the provided ID.
        """
        raise NotImplementedError("get_activity method must be implemented by subclasses.")

    @abstractmethod
    def list_activities(self, filters: dict) -> list[Activity]:
        """
        Retrieve activities matching optional filters.
        Args:
            filters (dict): Dictionary with optional keys: id, difficulty, activity_type.
        Returns:
            list[Activity]: Activities that match the filters.
        Raises:
            ActivityNotFoundException: If an ID filter is provided but no activity matches.
        """
        raise NotImplementedError("list_activities method must be implemented by subclasses.")

    @abstractmethod
    def create_activity(self, activity_data: dict) -> Activity:
        """
        Create a new activity with the provided data.
        Args:
            activity_data (dict): A dictionary containing activity attributes.
        Returns:
            Activity: The newly created activity object.
        Raises:
            ActivityCreationException: If there is an error during activity creation.
        """
        raise NotImplementedError("create_activity method must be implemented by subclasses.")

    @abstractmethod
    def create_activities(self, activities_data: list[dict]) -> list[Activity]:
        """
        Create multiple activities.
        Args:
            activities_data (list[dict]): List of activity payloads.
        Returns:
            list[Activity]: Created activities.
        """
        raise NotImplementedError("create_activities method must be implemented by subclasses.")

    @abstractmethod
    def update_activity(self, activity_id: uuid.UUID, update_data: dict) -> Activity:
        """
        Update an existing activity with the provided data.
        Args:
            activity_id (uuid.UUID): The ID of the activity to update.
            update_data (dict): A dictionary containing attributes to update.
        Returns:
            Activity: The updated activity object.
        Raises:
            ActivityNotFoundException: If no activity is found with the given ID.
            ActivityUpdateException: If there is an error during activity update.
        """
        raise NotImplementedError("update_activity method must be implemented by subclasses.")

    @abstractmethod
    def get_recommended_activities(self, patient: Patient) -> list[Activity]:
        """
        Retrieve recommended activities for a patient.
        Args:
            patient (Patient): The patient for whom to retrieve the recommended activities.
        Returns:
            list[Activity]: A list of recommended activities.
        Raises:
            ActivityNotFoundException: If no activities are available.
        """
        raise NotImplementedError("get_recommended_activities method must be implemented by subclasses.")

    @classmethod
    def get_instance(cls, inst: 'IActivityController' | None = None) -> 'IActivityController':
        """
        Get the singleton instance of the activity controller.
        Args:
            inst (IActivityController | None): Optional instance to set as the singleton.
        Returns:
            IActivityController: The instance of the activity controller.
        """
        if cls.__instance is None:
            cls.__instance = inst or ActivityController()
        return cls.__instance
    
class ActivityController(IActivityController):
    def get_activity(self, activity_id: uuid.UUID) -> Activity:
        activity = db.session.get(Activity, activity_id)
        if not activity:
            raise ActivityNotFoundException(f"No s'ha trobat cap activitat amb l'ID {activity_id}.")
        return activity

    def list_activities(self, filters: dict) -> list[Activity]:
        query = Activity.query

        activity_id = filters.get('id')
        activity_title = filters.get('title')
        difficulty = filters.get('difficulty')
        difficulty_min = filters.get('difficulty_min')
        difficulty_max = filters.get('difficulty_max')
        activity_type = filters.get('activity_type')

        if activity_id:
            query = query.filter(Activity.id == activity_id)
        if activity_title is not None:
            query = query.filter(Activity.title == activity_title)
        if difficulty is not None:
            query = query.filter(Activity.difficulty == difficulty)
        if difficulty_min is not None:
            query = query.filter(Activity.difficulty >= difficulty_min)
        if difficulty_max is not None:
            query = query.filter(Activity.difficulty <= difficulty_max)
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)

        activities = query.all()
        if activity_id and not activities:
            raise ActivityNotFoundException(f"No s'ha trobat cap activitat amb l'ID {activity_id}.")
        return activities

    def create_activity(self, activity_data: dict) -> Activity:
        try:
            activity_payload = {
                "id": uuid.uuid4(),
                **activity_data
            }
            activity = Activity(**activity_payload)
            return activity
        except Exception as exc:
            raise ActivityCreationException(f"No s'ha pogut crear l'activitat: {str(exc)}") from exc

    def create_activities(self, activities_data: list[dict]) -> list[Activity]:
        try:
            return [self.create_activity(activity_data) for activity_data in activities_data]
        except Exception as exc:
            raise ActivityCreationException(f"No s'han pogut crear les activitats: {str(exc)}") from exc

    def update_activity(self, activity_id: uuid.UUID, update_data: dict) -> Activity:
        activity = self.get_activity(activity_id)
        try:
            activity.set_properties(update_data)
        except Exception as exc:
            raise ActivityUpdateException(f"No s'ha pogut actualitzar l'activitat: {str(exc)}") from exc
        return activity

    def get_recommended_activities(self, patient: Patient) -> list[Activity]:
        query = Activity.query

        filters = patient.get_recommended_activity_filters()

        activity_type = filters.get('activity_type')
        difficulty = filters.get('difficulty')
        difficulty_min = filters.get('difficulty_min')
        difficulty_max = filters.get('difficulty_max')

        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        if difficulty is not None:
            query = query.filter(Activity.difficulty == difficulty)
        if difficulty_min is not None:
            query = query.filter(Activity.difficulty >= difficulty_min)
        if difficulty_max is not None:
            query = query.filter(Activity.difficulty <= difficulty_max)

        activities = query.all()
        if not activities:
            activities = Activity.query.all()

        if not activities:
            raise ActivityNotFoundException("No hi ha activitats disponibles a la base de dades.")
        
        return choice(activities)
