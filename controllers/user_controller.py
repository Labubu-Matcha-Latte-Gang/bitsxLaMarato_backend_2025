from __future__ import annotations
from abc import ABC, abstractmethod

from helpers.enums.user_role import UserRole
from helpers.exceptions.user_exceptions import UserAlreadyExistsException, UserNotFoundException
from helpers.factories.controller_factories import AbstractControllerFactory
from db import db
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
        user: User | None = db.session.get(User, email)
        if not user:
            raise UserNotFoundException("Usuari no trobat.")
        return user

    def create_user(self, user_data: dict) -> User:
        potential_existing_user = db.session.get(User, user_data.get('email'))
        if potential_existing_user:
            raise UserAlreadyExistsException("Ja existeix un usuari amb aquest correu.")
        
        user_payload = {
                "email": user_data['email'],
                "password": User.hash_password(user_data['password']),
                "name": user_data['name'],
                "surname": user_data['surname'],
            }
        new_user = User(**user_payload)
        return new_user

    def update_user(self, email: str, update_data: dict) -> User:
        user: User | None = db.session.get(User, email)
        if not user:
            raise UserNotFoundException("Usuari no trobat.")
        
        user.set_properties(update_data)
        role_instance = user.get_role_instance()
        role_type = role_instance.get_role()
        factory = AbstractControllerFactory.get_instance()
        match role_type:
            case UserRole.DOCTOR:
                controller = factory.get_doctor_controller()
                controller.update_doctor(user, update_data)
            case UserRole.PATIENT:
                controller = factory.get_patient_controller()
                controller.update_patient(user, update_data)

        return user
