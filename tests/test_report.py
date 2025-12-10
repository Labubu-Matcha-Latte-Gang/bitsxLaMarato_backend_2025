from __future__ import annotations

import pytest

from application.services.token_service import TokenService
from helpers.exceptions.user_exceptions import ExpiredTokenException
from helpers.factories import adapter_factories
from helpers.factories.adapter_factories import AbstractAdapterFactory
from helpers.graphic_adapter import AbstractGraphicAdapter
from helpers.llm_adapter import AbstractLlmAdapter
from helpers.pdf_generator_adapter import AbstractPDFGeneratorAdapter
from helpers.qr_adapter import QRAdapter
from tests.base_test import BaseTest


class _StubGraphicAdapter(AbstractGraphicAdapter):
    def create_score_graphs(self, scores):
        return {}

    def create_question_graphs(self, answers):
        return {}


class _StubPDFAdapter(AbstractPDFGeneratorAdapter):
    def __init__(self, payload: bytes):
        self.payload = payload

    def generate_patient_report(self, patient_data, date, llm_summary, template_path='templates/patient_report.html'):
        return self.payload


class _StubLLMAdapter(AbstractLlmAdapter):
    def generate_summary(self, patient_data, system_prompt):
        return "Resum integrat per a proves."


class _StubAdapterFactory(AbstractAdapterFactory):
    def __init__(self):
        self.pdf_bytes = b"%PDF-1.4\n%BITS"
        self._graphic_adapter = _StubGraphicAdapter()
        self._pdf_adapter = _StubPDFAdapter(self.pdf_bytes)
        self._llm_adapter = _StubLLMAdapter()
        self._qr_adapter = QRAdapter()

    def get_graphic_adapter(self):
        return self._graphic_adapter

    def get_qr_adapter(self):
        return self._qr_adapter

    def get_pdf_generator_adapter(self):
        return self._pdf_adapter

    def get_llm_adapter(self):
        return self._llm_adapter


@pytest.fixture()
def stub_adapter_factory(monkeypatch):
    """
    Replace the default adapter factory so PDF/LLM generation stays local to the test suite.
    """
    stub = _StubAdapterFactory()

    def _get_instance(cls):
        return stub

    monkeypatch.setattr(
        adapter_factories.AbstractAdapterFactory,
        "_AbstractAdapterFactory__instance",
        stub,
        raising=False,
    )
    monkeypatch.setattr(
        adapter_factories.AbstractAdapterFactory,
        "get_instance",
        classmethod(_get_instance),
    )
    return stub


class TestReportResource(BaseTest):
    def _report_url(self, email: str) -> str:
        return f"{self.api_prefix}/report/{email}"

    def test_patient_can_download_pdf_report(self, stub_adapter_factory):
        patient = self.create_patient_model()
        token = self.generate_token(patient.email)

        response = self.client.get(
            self._report_url(patient.email),
            query_string={"access_token": token, "timezone": "Europe/Madrid"},
        )

        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert response.data == stub_adapter_factory.pdf_bytes
        disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in disposition
        expected_identifier = f"{patient.name}_{patient.surname}"
        assert expected_identifier in disposition

    def test_missing_access_token_returns_401(self, stub_adapter_factory):
        patient = self.create_patient_model()

        response = self.client.get(self._report_url(patient.email))

        assert response.status_code == 401
        body = response.get_json()
        assert "token" in (body or {}).get("message", "").lower()

    def test_invalid_token_returns_401(self, stub_adapter_factory):
        patient = self.create_patient_model()

        response = self.client.get(
            self._report_url(patient.email),
            query_string={"access_token": "invalid-token"},
        )

        assert response.status_code == 401
        body = response.get_json()
        assert "invàlid" in (body or {}).get("message", "").lower()

    def test_expired_token_returns_401(self, stub_adapter_factory, monkeypatch):
        patient = self.create_patient_model()
        token = self.generate_token(patient.email)

        def _expired_parse(self, token_value):
            raise ExpiredTokenException("El token ha caducat.")

        monkeypatch.setattr(TokenService, "parse", _expired_parse)

        response = self.client.get(
            self._report_url(patient.email),
            query_string={"access_token": token, "timezone": "Europe/Madrid"},
        )

        assert response.status_code == 401
        body = response.get_json()
        assert "caducat" in (body or {}).get("message", "").lower()

    def test_patient_cannot_access_other_patient_report(self, stub_adapter_factory):
        owner = self.create_patient_model()
        outsider = self.create_patient_model()
        token = self.generate_token(outsider.email)

        response = self.client.get(
            self._report_url(owner.email),
            query_string={"access_token": token, "timezone": "Europe/Madrid"},
        )

        assert response.status_code == 403
        body = response.get_json()
        assert "permís" in (body or {}).get("message", "").lower()

    def test_invalid_timezone_returns_400(self, stub_adapter_factory):
        patient = self.create_patient_model()
        token = self.generate_token(patient.email)

        response = self.client.get(
            self._report_url(patient.email),
            query_string={"access_token": token, "timezone": "Mars/Base"},
        )

        assert response.status_code == 400
        body = response.get_json() or {}
        message = body.get("message", "").lower()
        assert message
