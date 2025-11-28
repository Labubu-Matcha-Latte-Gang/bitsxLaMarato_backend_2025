from abc import ABC, abstractmethod
from globals import APPLICATION_EMAIL, RESET_CODE_VALIDITY_MINUTES, RESET_PASSWORD_FRONTEND_PATH
from helpers.email_service.adapter import AbstractEmailAdapter
from helpers.forgot_password.user_service import UserService

class AbstractForgotPasswordFacade(ABC):
    """
    Abstract facade for forgot password functionality.
    """
    __instance: 'AbstractForgotPasswordFacade' = None

    @classmethod
    def get_instance(
        cls,
        user_service: UserService | None = None,
        email_service: AbstractEmailAdapter | None = None,
        refresh: bool = False
    ) -> 'AbstractForgotPasswordFacade':
        """
        Get (or rebuild) the forgot password facade instance.
        Args:
            user_service (UserService | None): Optional user service to inject.
            email_service (AbstractEmailAdapter | None): Optional email adapter to inject.
            refresh (bool): If True, forces recreation even when an instance already exists.
        """
        if refresh or cls.__instance is None or user_service is not None or email_service is not None:
            cls.__instance = ForgotPasswordFacade(
                user_service or UserService.get_instance(),
                email_service or AbstractEmailAdapter.get_instance()
            )
        return cls.__instance
    
    @abstractmethod
    def process_forgot_password(self, email: str, from_email: str, subject: str, body_template: str) -> None:
        """
        Process the forgot password request by generating a reset code and sending an email.
        Args:
            email (str): The email address of the user who forgot their password.
            from_email (str): The sender email address.
            subject (str): The subject of the email.
            body_template (str): The email body template containing a placeholder for the reset code.
        Raises:
            SendEmailException: If there is an error sending the email.
            UserNotFoundException: If the user with the given email is not found.
        """
        raise NotImplementedError("process_forgot_password method must be implemented by subclasses.")
    
    @abstractmethod
    def reset_password(self, email: str, reset_code: str, new_password: str) -> None:
        """
        Reset the user's password.
        Args:
            email (str): The email address of the user.
            reset_code (str): The reset code provided by the user.
            new_password (str): The new password to set.
        Raises:
            UserNotFoundException: If the user with the given email is not found.
            InvalidResetCodeException: If the reset code is invalid or expired.
        """
        raise NotImplementedError("reset_password method must be implemented by subclasses.")

class ForgotPasswordFacade(AbstractForgotPasswordFacade):
    __user_service: UserService
    __email_service: AbstractEmailAdapter

    def __init__(self, user_service: UserService, email_service: AbstractEmailAdapter):
        self.__user_service = user_service
        self.__email_service = email_service

    
    def process_forgot_password(self, email: str, from_email: str, subject: str, body_template: str) -> None:
        reset_code = self.__user_service.user_forgot_password(email)
        body = body_template.format(
            reset_code=reset_code,
            reset_url=RESET_PASSWORD_FRONTEND_PATH,
            support_email=from_email or APPLICATION_EMAIL,
            code_validity=RESET_CODE_VALIDITY_MINUTES
        )
        self.__email_service.send_email([email], from_email, subject, body)

    def reset_password(self, email: str, reset_code: str, new_password: str) -> None:
        return self.__user_service.user_reset_password(email, reset_code, new_password)
