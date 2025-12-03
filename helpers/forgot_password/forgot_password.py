from abc import ABC, abstractmethod

from application.container import ServiceFactory
from application.services.password_reset_service import PasswordResetService
from globals import APPLICATION_EMAIL, RESET_CODE_VALIDITY_MINUTES, RESET_PASSWORD_FRONTEND_PATH
from helpers.email_service.adapter import AbstractEmailAdapter

class AbstractForgotPasswordFacade(ABC):
    """
    Abstract facade for forgot password functionality.
    """
    __instance: 'AbstractForgotPasswordFacade' = None

    @classmethod
    def get_instance(
        cls,
        reset_service: PasswordResetService | None = None,
        email_service: AbstractEmailAdapter | None = None,
        refresh: bool = False
    ) -> 'AbstractForgotPasswordFacade':
        """
        Get (or rebuild) the forgot password facade instance.
        Args:
            reset_service (PasswordResetService | None): Optional reset service to inject.
            email_service (AbstractEmailAdapter | None): Optional email adapter to inject.
            refresh (bool): If True, forces recreation even when an instance already exists.
        """
        if refresh or cls.__instance is None or reset_service is not None or email_service is not None:
            service = reset_service or ServiceFactory().build_password_reset_service(RESET_CODE_VALIDITY_MINUTES)
            cls.__instance = ForgotPasswordFacade(
                service,
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
    __reset_service: PasswordResetService
    __email_service: AbstractEmailAdapter

    def __init__(self, reset_service: PasswordResetService, email_service: AbstractEmailAdapter):
        self.__reset_service = reset_service
        self.__email_service = email_service

    
    def process_forgot_password(self, email: str, from_email: str, subject: str, body_template: str) -> None:
        reset_code = self.__reset_service.generate_reset_code(email)
        body = body_template.replace("{reset_code}", reset_code).replace("{reset_url}", RESET_PASSWORD_FRONTEND_PATH).replace("{support_email}", from_email or APPLICATION_EMAIL).replace("{code_validity}", str(RESET_CODE_VALIDITY_MINUTES))
        self.__email_service.send_email([email], from_email, subject, body)

    def reset_password(self, email: str, reset_code: str, new_password: str) -> None:
        return self.__reset_service.reset_password(email, reset_code, new_password)
