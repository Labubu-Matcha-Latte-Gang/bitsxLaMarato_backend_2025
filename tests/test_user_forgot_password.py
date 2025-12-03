import re
from datetime import datetime, timedelta, timezone
from typing import Sequence
from unittest.mock import patch

import pytest

from globals import RESET_CODE_VALIDITY_MINUTES
from helpers.email_service.adapter import AbstractEmailAdapter
from models.associations import UserCodeAssociation
from tests.base_test import BaseTest


class InMemoryEmailAdapter(AbstractEmailAdapter):
    def __init__(self):
        self.sent_messages: list[dict[str, str | list[str]]] = []

    def send_email(self, to_emails: Sequence[str], from_email: str, subject: str, body: str) -> None:
        recipients = list(to_emails)
        self.sent_messages.append(
            {
                "to": recipients,
                "from": from_email,
                "subject": subject,
                "body": body,
            }
        )

    @property
    def last_message(self) -> dict[str, str | list[str]] | None:
        return self.sent_messages[-1] if self.sent_messages else None


class TestUserForgotPassword(BaseTest):
    @pytest.fixture(autouse=True)
    def _setup_forgot_password_facade(self):
        # Reset singletons and inject in-memory email adapter to avoid external calls
        AbstractEmailAdapter._AbstractEmailAdapter__instance = None

        self.email_adapter = InMemoryEmailAdapter()
        AbstractEmailAdapter._AbstractEmailAdapter__instance = self.email_adapter
        yield
        AbstractEmailAdapter._AbstractEmailAdapter__instance = None

    def _request_forgot_password(self, email: str):
        return self.client.post(f"{self.api_prefix}/user/forgot-password", json={"email": email})

    def _request_reset_password(self, email: str, reset_code: str, new_password: str):
        payload = {"email": email, "reset_code": reset_code, "new_password": new_password}
        return self.client.patch(f"{self.api_prefix}/user/forgot-password", json=payload)

    def _extract_code_from_email(self) -> str:
        message = self.email_adapter.last_message
        assert message is not None, "No email was captured"
        body: str = message["body"]  # type: ignore[assignment]
        match = re.search(r'class="code">([A-Za-z0-9]{8})<', body)
        assert match, "Reset code not found in email body"
        return match.group(1)

    @patch('globals.APPLICATION_EMAIL', 'test@example.com')
    def test_forgot_password_sends_email_and_stores_code(self):
        user = self.create_patient_model()

        response = self._request_forgot_password(user.email)

        assert response.status_code == 200
        body = response.get_json() or {}
        assert body.get("validity") == RESET_CODE_VALIDITY_MINUTES
        assert len(self.email_adapter.sent_messages) == 1
        sent = self.email_adapter.last_message
        assert sent is not None
        assert sent["to"] == [user.email]

        reset_code = self._extract_code_from_email()
        association = self.db.get(UserCodeAssociation, user.email)
        assert association is not None
        assert association.check_code(reset_code)
        assert association.is_expired(datetime.now(timezone.utc)) is False

    def test_forgot_password_unknown_user_returns_404(self):
        response = self._request_forgot_password("missing@example.com")

        assert response.status_code == 404
        assert self.email_adapter.last_message is None
        assert self.db.get(UserCodeAssociation, "missing@example.com") is None

    @patch('globals.APPLICATION_EMAIL', 'test@example.com')
    def test_multiple_requests_replace_previous_code(self):
        user = self.create_patient_model()

        first_response = self._request_forgot_password(user.email)
        assert first_response.status_code == 200
        first_code = self._extract_code_from_email()

        second_response = self._request_forgot_password(user.email)
        assert second_response.status_code == 200
        second_code = self._extract_code_from_email()

        assert len(self.email_adapter.sent_messages) == 2
        assert first_code != second_code

        association = self.db.get(UserCodeAssociation, user.email)
        assert association is not None
        assert association.check_code(second_code)
        assert association.check_code(first_code) is False

        invalid_reset = self._request_reset_password(user.email, first_code, "NewPass1A")
        assert invalid_reset.status_code == 400

    @patch('globals.APPLICATION_EMAIL', 'test@example.com')
    def test_reset_password_with_valid_code_changes_password(self):
        user = self.create_patient_model()
        forgot_response = self._request_forgot_password(user.email)
        assert forgot_response.status_code == 200
        reset_code = self._extract_code_from_email()

        reset_response = self._request_reset_password(user.email, reset_code, "BetterPass1")

        assert reset_response.status_code == 200
        assert self.db.get(UserCodeAssociation, user.email) is None

        login_response = self.login(user.email, "BetterPass1")
        assert login_response.status_code == 200

        old_login_response = self.login(user.email, self.default_password)
        assert old_login_response.status_code == 401

    @patch('globals.APPLICATION_EMAIL', 'test@example.com')
    def test_reset_password_with_expired_code_returns_400_and_deletes_code(self):
        user = self.create_patient_model()
        self._request_forgot_password(user.email)
        reset_code = self._extract_code_from_email()

        association = self.db.get(UserCodeAssociation, user.email)
        assert association is not None
        association.expiration = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.db.commit()

        response = self._request_reset_password(user.email, reset_code, "AnotherPass1")

        assert response.status_code == 400
        assert self.db.get(UserCodeAssociation, user.email) is None

    def test_reset_password_with_invalid_code_returns_400_and_keeps_association(self):
        user = self.create_patient_model()
        self._request_forgot_password(user.email)

        response = self._request_reset_password(user.email, "Invalid1", "AnotherPass2")

        assert response.status_code == 400
        association = self.db.get(UserCodeAssociation, user.email)
        assert association is not None
        assert association.is_expired(datetime.now(timezone.utc)) is False

    def test_reset_password_unknown_user_returns_404(self):
        response = self._request_reset_password("unknown@example.com", "ABCDEFGH", "Passw0rd1")

        assert response.status_code == 404
        assert self.email_adapter.last_message is None

    def test_forgot_password_with_missing_application_email_returns_500(self):
        user = self.create_patient_model()

        response = self._request_forgot_password(user.email)

        assert response.status_code == 500
        response_data = response.get_json()
        assert response_data is not None
        assert "error" in response_data

    def test_forgot_password_with_missing_email_field_returns_400(self):
        response = self.client.post(f"{self.api_prefix}/user/forgot-password", json={})

        assert response.status_code == 400

    def test_reset_password_with_missing_fields_returns_400(self):
        # Missing reset_code
        response = self.client.patch(
            f"{self.api_prefix}/user/forgot-password",
            json={"email": "test@example.com", "new_password": "NewPass1"}
        )
        assert response.status_code == 400

        # Missing new_password
        response = self.client.patch(
            f"{self.api_prefix}/user/forgot-password",
            json={"email": "test@example.com", "reset_code": "ABC12345"}
        )
        assert response.status_code == 400

        # Missing email
        response = self.client.patch(
            f"{self.api_prefix}/user/forgot-password",
            json={"reset_code": "ABC12345", "new_password": "NewPass1"}
        )
        assert response.status_code == 400
