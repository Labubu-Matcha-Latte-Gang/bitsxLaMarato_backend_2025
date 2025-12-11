from helpers.exceptions.base import ApplicationException


class SendEmailException(ApplicationException):
    """Exception raised for errors in the email sending process."""


class SMTPCredentialsException(ApplicationException):
    """Exception raised for SMTP credential related errors."""
