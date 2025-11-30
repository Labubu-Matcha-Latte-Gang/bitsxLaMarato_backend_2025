from abc import ABC, abstractmethod
from helpers.enums.user_role import UserRole


class IUserRole(ABC):
    """
    Interface for user roles
    """
    @abstractmethod
    def get_user(self):
        """
        Get the associated User object
        Returns:
            User: The associated User object
        """
        raise NotImplementedError()

    @abstractmethod
    def get_email(self) -> str:
        """
        Get the email for this role
        Returns:
            str: The email for this role
        """
        raise NotImplementedError()

    @abstractmethod
    def set_email(self, new_email: str) -> None:
        """
        Set a new email for this role
        Args:
            new_email (str): The new email to set
        """
        raise NotImplementedError()

    @abstractmethod
    def to_dict(self) -> dict:
        """
        Convert the role to a dictionary representation
        Returns:
            dict: The dictionary representation of the role
        """
        raise NotImplementedError()

    @abstractmethod
    def get_role(self) -> UserRole:
        """
        Get the role of this user
        Returns:
            UserRole: The role of this user
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_all_associations_between_user_roles(self) -> None:
        """
        Remove all associations between user roles for this role
        """
        raise NotImplementedError()

    @abstractmethod
    def set_properties(self, data: dict) -> None:
        """
        Set multiple properties for the role from a dictionary
        Args:
            data (dict): A dictionary containing the properties to set
        """
        raise NotImplementedError()

    @abstractmethod
    def doctor_of_this_patient(self, patient) -> bool:
        """
        Checks if the role grants access to the provided patient
        """
        raise NotImplementedError()
