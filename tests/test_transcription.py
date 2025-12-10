from __future__ import annotations

import io
import wave
from types import SimpleNamespace
from uuid import uuid4

import pytest
import resources.transcription as transcription_resource
from helpers.enums.question_types import QuestionType
from models.associations import QuestionAnsweredAssociation
from models.transcription import TranscriptionChunk
from tests.base_test import BaseTest


class TestTranscriptionResource(BaseTest):
    def _sample_wav_file(self) -> io.BytesIO:
        """Generate a minimal mono 16 kHz WAV payload for uploads."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 160)
        buffer.seek(0)
        return buffer

    def _stub_transcription_dependencies(self, monkeypatch, transcript_text: str = "chunk text") -> None:
        """Bypass OpenAI and analysis engines so tests stay deterministic."""

        def fake_create(**_kwargs):
            return SimpleNamespace(
                text=transcript_text,
                segments=[SimpleNamespace(start=0.42)],
            )

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=fake_create),
            )
        )

        monkeypatch.setattr(transcription_resource, "get_azure_client", lambda: fake_client)
        monkeypatch.setattr(
            transcription_resource,
            "analyze_audio_signal",
            lambda _path: {"speech_energy": 0.8},
        )
        monkeypatch.setattr(
            transcription_resource,
            "analyze_linguistics",
            lambda text: {"lexical_density": len(text)},
        )
        monkeypatch.setattr(
            transcription_resource,
            "analyze_executive_functions",
            lambda text: {"coherence": round(len(text) / 10, 2)},
        )

    def _create_question(self) -> str:
        admin = self.create_admin()
        token = self.login_and_get_token(admin.email, self.default_password)
        payload = {
            "questions": [
                {
                    "text": f"Pregunta transcripció {uuid4().hex[:6]}",
                    "question_type": QuestionType.CONCENTRATION.value,
                    "difficulty": 2.0,
                }
            ]
        }
        resp = self.client.post(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            json=payload,
        )
        assert resp.status_code == 201
        return resp.get_json()[0]["id"]

    def test_chunk_upload_saves_transcription_chunk(self, monkeypatch):
        self._stub_transcription_dependencies(monkeypatch, transcript_text="Hola chunk")
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        session_id = "session-chunk"
        wav_file = self._sample_wav_file()
        data = {
            "session_id": session_id,
            "chunk_index": "0",
            "audio_blob": (wav_file, "chunk.wav"),
        }
        response = self.client.post(
            f"{self.api_prefix}/transcription/chunk",
            headers=self.auth_headers(token),
            data=data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "success"
        assert body["partial_text"] == "Hola chunk"
        assert "speech_energy" in body["analysis"]
        assert "lexical_density" in body["analysis"]
        assert body["analysis"]["raw_latency"] == pytest.approx(0.42)

        stored_chunk = (
            self.db.query(TranscriptionChunk)
            .filter_by(session_id=session_id, chunk_index=0)
            .one()
        )
        assert stored_chunk.text == "Hola chunk"
        assert stored_chunk.analysis["speech_energy"] == 0.8

    def test_complete_transcription_records_answer_and_cleans_chunks(self, monkeypatch):
        transcript_text = "Resposta final"
        self._stub_transcription_dependencies(monkeypatch, transcript_text=transcript_text)

        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])
        question_id = self._create_question()

        session_id = "session-complete"
        wav_file = self._sample_wav_file()
        chunk_data = {
            "session_id": session_id,
            "chunk_index": "0",
            "audio_blob": (wav_file, "chunk.wav"),
        }
        chunk_resp = self.client.post(
            f"{self.api_prefix}/transcription/chunk",
            headers=self.auth_headers(token),
            data=chunk_data,
            content_type="multipart/form-data",
        )
        assert chunk_resp.status_code == 200

        complete_resp = self.client.post(
            f"{self.api_prefix}/transcription/complete",
            headers=self.auth_headers(token),
            json={"session_id": session_id, "question_id": question_id},
        )

        assert complete_resp.status_code == 200
        body = complete_resp.get_json()
        assert body["status"] == "completed"
        assert body["transcription"] == transcript_text
        assert body["analysis"]["lexical_density"] == len(transcript_text)
        assert body["analysis"]["coherence"] == round(len(transcript_text) / 10, 2)
        assert body["question_id"] == str(question_id)

        remaining_chunks = (
            self.db.query(TranscriptionChunk).filter_by(session_id=session_id).count()
        )
        assert remaining_chunks == 0

        association = (
            self.db.query(QuestionAnsweredAssociation)
            .filter_by(patient_email=patient_payload["email"])
            .one()
        )
        assert association.answer_text == transcript_text
        assert association.analysis["coherence"] == round(len(transcript_text) / 10, 2)
