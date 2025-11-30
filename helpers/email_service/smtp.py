import smtplib
import ssl
from email.message import EmailMessage
from typing import Sequence

from globals import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USERNAME, SMTP_USE_SSL, SMTP_USE_TLS
from helpers.debugger.logger import AbstractLogger
from helpers.email_service.adapter import AbstractEmailAdapter
from helpers.exceptions.mail_exceptions import SMTPCredentialsException, SendEmailException


class SmtpEmailAdapter(AbstractEmailAdapter):
    """
    Concrete email adapter that sends messages using an SMTP server.
    """

    logger = AbstractLogger.get_instance()

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        use_ssl: bool | None = None,
    ):
        self.__host = host or SMTP_HOST
        self.__port = port or SMTP_PORT
        self.__username = username or SMTP_USERNAME
        self.__password = password or SMTP_PASSWORD
        self.__use_tls = SMTP_USE_TLS if use_tls is None else use_tls
        self.__use_ssl = SMTP_USE_SSL if use_ssl is None else use_ssl

        if not self.__host or not self.__port:
            raise SMTPCredentialsException("SMTP_HOST and SMTP_PORT must be configured.")

        # SSL and STARTTLS are mutually exclusive; SSL wins when explicitly requested.
        if self.__use_ssl:
            self.__use_tls = False

    def __build_email(self, to_email: str, from_email: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject

        if self._is_html(body):
            message.set_content(body, subtype="html")
        else:
            message.set_content(body)
        return message

    def __connect(self) -> smtplib.SMTP:
        """
        Establish and return a configured SMTP connection.
        """
        try:
            if self.__use_ssl:
                smtp = smtplib.SMTP_SSL(self.__host, self.__port, context=ssl.create_default_context())
            else:
                smtp = smtplib.SMTP(self.__host, self.__port)
                smtp.ehlo()
                if self.__use_tls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()

            if self.__username and self.__password:
                smtp.login(self.__username, self.__password)

            return smtp
        except Exception as e:
            self.logger.error(
                message="Failed to connect to SMTP server",
                metadata={"host": self.__host, "port": self.__port, "username": self.__username},
                module=__name__,
                error=e,
            )
            raise SMTPCredentialsException(f"Failed to connect to SMTP server: {e}") from e

    def send_email(self, to_emails: Sequence[str], from_email: str, subject: str, body: str) -> None:
        recipients = list(to_emails)
        if not recipients:
            raise SendEmailException("No recipients provided for SMTP email.")

        try:
            with self.__connect() as smtp:
                for recipient in recipients:
                    message = self.__build_email(recipient, from_email, subject, body)
                    smtp.send_message(message)
                self.logger.info(
                    message="Email sent successfully via SMTP",
                    metadata={
                        "to_emails": recipients,
                        "from_email": from_email,
                        "subject": subject,
                        "body": body,
                        "host": self.__host,
                        "port": self.__port,
                        "username": self.__username,
                        "secured_with": "ssl" if self.__use_ssl else ("starttls" if self.__use_tls else "plain"),
                    },
                    module=__name__,
                )
        except Exception as e:
            self.logger.error(
                message="Error sending email via SMTP",
                metadata={
                    "to_emails": list(to_emails),
                    "from_email": from_email,
                    "subject": subject,
                    "body": body,
                    "host": self.__host,
                    "port": self.__port,
                    "username": self.__username,
                },
                module=__name__,
                error=e,
            )
            if isinstance(e, SendEmailException):
                raise
            raise SendEmailException(f"Error sending email via SMTP: {e}") from e
