from abc import ABC, abstractmethod
from typing import Sequence

from helpers.email_service.send_grid import SendGridEmailAdapter


class AbstractEmailAdapter(ABC):
    __instance: 'AbstractEmailAdapter' = None

    @abstractmethod
    def send_email(self, to_emails: Sequence[str], from_email: str, subject: str, body: str) -> None:
        """
        Send an email.
        Args:
            to_emails (Sequence[str]): List of recipient email addresses.
            from_email (str): Sender email address.
            subject (str): Subject of the email.
            body (str): Body content of the email.
        Raises:
            SendEmailException: If there is an error sending the email.
        """
        raise NotImplementedError("send_email method must be implemented by subclasses.")
    
    @classmethod
    def get_instance(cls) -> 'AbstractEmailAdapter':
        """
        Get the singleton instance of the email adapter.
        Returns:
            AbstractEmailAdapter: The instance of the email adapter.
        """
        if cls.__instance is None:
            cls.__instance = SendGridEmailAdapter()
        return cls.__instance