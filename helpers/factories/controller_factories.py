from abc import ABC, abstractmethod

from controllers.user_controller import IUserController, UserController

class AbstractControllerFactory(ABC):
    __instance: 'AbstractControllerFactory' = None

    @classmethod
    def get_instance(cls, inst: 'AbstractControllerFactory' | None = None) -> 'AbstractControllerFactory':
        """
        Get the singleton instance of the controller factory.
        Args:
            inst (AbstractControllerFactory | None): Optional instance to set as the singleton.
        Returns:
            AbstractControllerFactory: The instance of the controller factory.
        """
        if cls.__instance is None:
            cls.__instance = inst or ControllerFactory()
        return cls.__instance
    
    @abstractmethod
    def get_user_controller(self) -> IUserController:
        """
        Get the user controller instance.
        Returns:
            IUserController: The user controller instance.
        """
        raise NotImplementedError("get_user_controller method must be implemented by subclasses.")

class ControllerFactory(AbstractControllerFactory):
    def get_user_controller(self) -> IUserController:
        return IUserController.get_instance(UserController())