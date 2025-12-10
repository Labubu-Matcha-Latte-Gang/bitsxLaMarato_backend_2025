from __future__ import annotations

from helpers.enums.qr_code_format import QRCodeFormat
from tests.base_test import BaseTest


class TestQRResource(BaseTest):
    def _qr_url(self) -> str:
        return f"{self.api_prefix}/qr"

    def _login_patient(self):
        patient = self.create_patient_model()
        token = self.login_and_get_token(patient.email, self.default_password)
        return patient, token

    def test_patient_can_generate_svg_qr(self):
        patient, token = self._login_patient()

        response = self.client.post(
            self._qr_url(),
            headers=self.auth_headers(token),
            json={"timezone": "Europe/Madrid"},
        )

        assert response.status_code == 200
        assert response.mimetype == "image/svg+xml"
        disposition = response.headers.get("Content-Disposition", "")
        assert patient.email.split("@")[0] in disposition
        assert response.data.startswith(b"<?xml")

    def test_patient_can_request_png_qr(self):
        _, token = self._login_patient()

        response = self.client.post(
            self._qr_url(),
            headers=self.auth_headers(token),
            json={"format": QRCodeFormat.PNG.value},
        )

        assert response.status_code == 200
        assert response.mimetype == "image/png"
        assert response.data.startswith(b"\x89PNG")

    def test_invalid_timezone_returns_500(self):
        _, token = self._login_patient()

        response = self.client.post(
            self._qr_url(),
            headers=self.auth_headers(token),
            json={"timezone": "Invalid/Zone"},
        )

        assert response.status_code == 500
        body = response.get_json()
        assert "zona horària" in (body or {}).get("message", "").lower()

    def test_access_requires_patient_role(self):
        doctor = self.create_doctor_model()
        token = self.login_and_get_token(doctor.email, self.default_password)

        response = self.client.post(
            self._qr_url(),
            headers=self.auth_headers(token),
            json={},
        )

        assert response.status_code == 403

    def test_missing_jwt_returns_401(self):
        response = self.client.post(
            self._qr_url(),
            json={},
        )

        assert response.status_code == 401

    def test_invalid_payload_triggers_422(self):
        _, token = self._login_patient()

        response = self.client.post(
            self._qr_url(),
            headers=self.auth_headers(token),
            json={"format": "pdf"},
        )

        assert response.status_code == 422
