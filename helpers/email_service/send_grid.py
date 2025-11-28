from typing import Sequence
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from bs4 import BeautifulSoup
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

    def __is_html(self, content: str) -> bool:
        """
        Check if the content is HTML.
        Args:
            content (str): The content to check.
        Returns:
            bool: True if the content is HTML, False otherwise.
        """
        bool_html = bool(BeautifulSoup(content, "html.parser").find())
        return bool_html
    
    def __build_email(self, to_emails: Sequence[str], from_email: str, subject: str, body: str) -> Mail:
        if self.__is_html(body):
            message = Mail(
                from_email=from_email,
                to_emails=to_emails,
                subject=subject,
                html_content=body
            )
        else:
            message = Mail(
                from_email=from_email,
                to_emails=to_emails,
                subject=subject,
                plain_text_content=body
            )
        return message
    
    def send_email(self, to_emails: Sequence[str], from_email: str, subject: str, body: str) -> None:
        message = self.__build_email(to_emails, from_email, subject, body)
        try:
            response: Response = self.__client.send(message)
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info(message=f"Email sent successfully via SendGrid", metadata={"to_emails": to_emails, "from_email": from_email, "subject": subject, "body": body, "response": {"status_code": response.status_code, "body": response.body.decode('utf-8')}}, module=__name__)
            else:
                raise SendEmailException(f"Failed to send email via SendGrid. Status code: {response.status_code}, Body: {response.body.decode('utf-8')}")
        except Exception as e:
            self.logger.error(message=f"Error sending email via SendGrid", metadata={"to_emails": to_emails, "from_email": from_email, "subject": subject, "body": body}, module=__name__, error=e)
            raise e