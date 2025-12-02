from abc import ABC, abstractmethod
import uuid

from helpers.exceptions.activity_exceptions import ActivityNotFoundException
from models.activity import Activity


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
        activity = Activity.query.get(activity_id)
        if not activity:
            raise ActivityNotFoundException(f"No activity found with ID {activity_id}.")
        return activity