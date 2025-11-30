from typing import Callable, TYPE_CHECKING

from helpers.exceptions.mail_exceptions import SendEmailException

if TYPE_CHECKING:
    from helpers.email_service.adapter import AbstractEmailAdapter

class EmailAdapterServiceLocator:
    """
    Service locator responsible for resolving concrete email adapters.
    """
    __instance: 'EmailAdapterServiceLocator' = None

    def __init__(self):
        self.__registry: dict[str, Callable[[], AbstractEmailAdapter]] = {}
        self.__bootstrap_defaults()

    @classmethod
    def get_instance(cls) -> 'EmailAdapterServiceLocator':
        if cls.__instance is None:
            cls.__instance = EmailAdapterServiceLocator()
        return cls.__instance

    def register(self, key: str, factory: Callable[[], AbstractEmailAdapter]) -> None:
        """
        Register a factory for a given adapter key.
        """
        self.__registry[key.lower()] = factory

    def resolve(self, key: str) -> AbstractEmailAdapter:
        """
        Resolve a concrete email adapter using the provided key.
        Raises:
            SendEmailException: If no adapter is registered for the given key.
        """
        normalized_key = key.lower()
        if normalized_key not in self.__registry:
            raise SendEmailException(f"No email adapter registered for key '{key}'")
        return self.__registry[normalized_key]()
    
    def __bootstrap_defaults(self) -> None:
        """
        Register built-in email adapters.
        """
        from helpers.email_service.send_grid import SendGridEmailAdapter
        from helpers.email_service.smtp import SmtpEmailAdapter

        self.register('sendgrid', SendGridEmailAdapter)
        self.register('smtp', SmtpEmailAdapter)
