class SendEmailException(Exception):
    """Exception raised for errors in the email sending process."""
    pass

class SMTPCredentialsException(Exception):
    """Exception raised for SMTP credential related errors."""
    pass