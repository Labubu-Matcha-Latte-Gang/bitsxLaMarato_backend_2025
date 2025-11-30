from abc import ABC, abstractmethod

from models.user import User

class IUserController(ABC):
    @abstractmethod
    def get_user(self, email: str) -> User:
        """
        Retrieve a user by their email.
        Args:
            email (str): The email of the user to retrieve.
        Returns:
            User: The user object corresponding to the provided email.
        Raises:
            UserNotFoundException: If no user is found with the given email.
        """
        raise NotImplementedError("get_user method must be implemented by subclasses.")
    
    @abstractmethod
    def create_user(self, user_data: dict) -> User:
        """
        Create a new user with the provided data.
        Args:
            user_data (dict): A dictionary containing user attributes.
        Returns:
            User: The newly created user object.
        Raises:
            UserCreationException: If there is an error during user creation.
        """
        raise NotImplementedError("create_user method must be implemented by subclasses.")
    
    @abstractmethod
    def update_user(self, email: str, update_data: dict) -> User:
        """
        Update an existing user with the provided data.
        Args:
            email (str): The email of the user to update.
            update_data (dict): A dictionary containing attributes to update.
        Returns:
            User: The updated user object.
        Raises:
            UserNotFoundException: If no user is found with the given email.
            UserUpdateException: If there is an error during user update.
        """
        raise NotImplementedError("update_user method must be implemented by subclasses.")