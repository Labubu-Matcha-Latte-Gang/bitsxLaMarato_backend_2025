from abc import ABC, abstractmethod

from models.user import User

class IUserController(ABC):
    __instance: 'IUserController' = None

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
    
    @classmethod
    def get_instance(cls, inst: 'IUserController' | None = None) -> 'IUserController':
        """
        Get the singleton instance of the user controller.
        Args:
            inst (IUserController | None): Optional instance to set as the singleton.
        Returns:
            IUserController: The instance of the user controller.
        """
        if cls.__instance is None:
            cls.__instance = inst or UserController()
        return cls.__instance
    
class UserController(IUserController):
    def get_user(self, email: str) -> User:
        # Implementation for retrieving a user by email
        pass

    def create_user(self, user_data: dict) -> User:
        # Implementation for creating a new user
        pass

    def update_user(self, email: str, update_data: dict) -> User:
        # Implementation for updating an existing user
        pass