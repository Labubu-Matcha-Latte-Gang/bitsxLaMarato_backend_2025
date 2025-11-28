from abc import ABC, abstractmethod

from helpers.forgot_password.forgot_password import ForgotPasswordFacade, AbstractForgotPasswordFacade


class AbstractForgotPasswordFactory(ABC):
    __instance: 'AbstractForgotPasswordFactory' = None

    @classmethod
    def get_instance(cls) -> 'AbstractForgotPasswordFactory':
        if cls.__instance is None:
            cls.__instance = ForgotPasswordFactory()
        return cls.__instance
    
    @abstractmethod
    def get_password_facade(
        self,
        user_service=None,
        email_service=None,
        refresh: bool = False
    ) -> AbstractForgotPasswordFacade:
        """
        Get the forgot password facade instance.
        Returns:
            AbstractForgotPasswordFacade: The forgot password facade instance.
        """
        raise NotImplementedError("get_password_facade method must be implemented by subclasses.")

class ForgotPasswordFactory(AbstractForgotPasswordFactory):
    def get_password_facade(self, user_service=None, email_service=None, refresh: bool = False) -> ForgotPasswordFacade:
        return ForgotPasswordFacade.get_instance(user_service=user_service, email_service=email_service, refresh=refresh)
