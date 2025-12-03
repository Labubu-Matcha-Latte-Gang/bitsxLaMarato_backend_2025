from typing import Sequence
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from python_http_client.client import Response

from globals import SENDGRID_API_KEY
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.mail_exceptions import SendEmailException
from helpers.email_service.adapter import AbstractEmailAdapter

class SendGridEmailAdapter(AbstractEmailAdapter):
    logger = AbstractLogger.get_instance()
    __client: SendGridAPIClient

    def __init__(self, api_key: str | None = None):
        api_key = api_key or SENDGRID_API_KEY
        self.__client = SendGridAPIClient(api_key)
    
    def __build_email(self, to_email: str, from_email: str, subject: str, body: str) -> Mail:
        payload = {
            "from_email": from_email,
            "to_emails": [to_email],
            "subject": subject,
        }
        if self._is_html(body):
            payload["html_content"] = body
        else:
            payload["plain_text_content"] = body
        return Mail(**payload)
    
    def send_email(self, to_emails: Sequence[str], from_email: str, subject: str, body: str) -> None:
        recipients = list(to_emails)
        if not recipients:
            raise SendEmailException("No s'ha proporcionat cap destinatari per al correu de SendGrid.")
        try:
            for recipient in recipients:
                message = self.__build_email(recipient, from_email, subject, body)
                response: Response = self.__client.send(message)
                if response.status_code < 200 or response.status_code >= 300:
                    raise SendEmailException(
                        f"No s'ha pogut enviar el correu via SendGrid. Codi d'estat: {response.status_code}, Cos: {response.body.decode('utf-8')}"
                    )
            self.logger.info(
                message="Email sent successfully via SendGrid",
                metadata={
                    "to_emails": recipients,
                    "from_email": from_email,
                    "subject": subject,
                    "body": body,
                },
                module=__name__,
            )
        except Exception as e:
            self.logger.error(
                message="Error sending email via SendGrid",
                metadata={
                    "to_emails": recipients,
                    "from_email": from_email,
                    "subject": subject,
                    "body": body,
                },
                module=__name__,
                error=e,
            )
            raise
