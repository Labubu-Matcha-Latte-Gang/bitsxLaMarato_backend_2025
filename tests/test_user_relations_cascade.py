from __future__ import annotations

import uuid
from datetime import datetime, timezone

from helpers.enums.question_types import QuestionType
from models.associations import DoctorPatientAssociation, QuestionAnsweredAssociation
from models.doctor import Doctor
from models.patient import Patient
from models.question import Question
from models.score import Score
from tests.base_test import BaseTest


class TestUserRelationsCascade(BaseTest):
    def _create_question(self, admin_token: str) -> str:
        payload = {
            "questions": [
                {
                    "text": f"Pregunta cascada {uuid.uuid4().hex[:8]}",
                    "question_type": QuestionType.CONCENTRATION.value,
                    "difficulty": 1.0,
                }
            ]
        }
        resp = self.client.post(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(admin_token),
            json=payload,
        )
        assert resp.status_code == 201
        return resp.get_json()[0]["id"]

    def _create_activity(self, admin_token: str) -> str:
        payload = {
            "activities": [
                {
                    "title": f"Activitat cascada {uuid.uuid4().hex[:8]}",
                    "description": "Descripcio de prova",
                    "activity_type": QuestionType.CONCENTRATION.value,
                    "difficulty": 2.0,
                }
            ]
        }
        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(admin_token),
            json=payload,
        )
        assert resp.status_code == 201
        return resp.get_json()[0]["id"]

    def test_delete_patient_clears_doctors_and_answers(self):
        # Arrange: doctor, patient linked to doctor, answered question, and completed activity with score
        doctor_payload = self.make_doctor_payload()
        doctor_resp = self.register_doctor(doctor_payload)
        assert doctor_resp.status_code == 201

        patient_payload = self.make_patient_payload(doctors=[doctor_payload["email"]])
        patient_resp = self.register_patient(patient_payload)
        assert patient_resp.status_code == 201
        patient_token = self.login_and_get_token(
            patient_payload["email"], patient_payload["password"]
        )

        admin = self.create_admin()
        admin_token = self.login_and_get_token(admin.email, self.default_password)
        question_id = self._create_question(admin_token)
        activity_id = self._create_activity(admin_token)

        patient_model = self.db.get(Patient, patient_payload["email"])
        question_model = self.db.get(Question, uuid.UUID(question_id))
        assert patient_model and question_model
        patient_model.add_answered_questions({question_model}, answered_at=datetime.now(timezone.utc))
        self.db.flush()

        # Complete activity to create a Score
        complete_resp = self.client.post(
            f"{self.api_prefix}/activity/complete",
            headers=self.auth_headers(patient_token),
            json={
                "id": activity_id,
                "score": 8.0,
                "seconds_to_finish": 20.0,
            },
        )
        assert complete_resp.status_code == 200

        # Verify Score exists before deletion
        activity_uuid = uuid.UUID(activity_id)
        pre_delete_score_count = (
            self.db.query(Score)
            .filter(Score.patient_email == patient_payload["email"])
            .filter(Score.activity_id == activity_uuid)
            .count()
        )
        assert pre_delete_score_count == 1

        # Act: delete patient (should cascade associations/answers/scores)
        delete_resp = self.client.delete(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(patient_token),
        )

        # Assert
        assert delete_resp.status_code == 204
        assert self.db.get(Patient, patient_payload["email"]) is None
        # Doctor remains but link is gone
        assert self.db.get(Doctor, doctor_payload["email"]) is not None
        assert (
            self.db.query(DoctorPatientAssociation)
            .filter(DoctorPatientAssociation.patient_email == patient_payload["email"])
            .count()
            == 0
        )
        assert (
            self.db.query(QuestionAnsweredAssociation)
            .filter(QuestionAnsweredAssociation.patient_email == patient_payload["email"])
            .count()
            == 0
        )
        # Verify Score is also deleted
        assert (
            self.db.query(Score)
            .filter(Score.patient_email == patient_payload["email"])
            .count()
            == 0
        )

    def test_delete_doctor_clears_patient_links(self):
        # Arrange: patient exists and is linked to doctor
        patient_payload = self.make_patient_payload()
        patient_resp = self.register_patient(patient_payload)
        assert patient_resp.status_code == 201

        doctor_payload = self.make_doctor_payload(patients=[patient_payload["email"]])
        doctor_resp = self.register_doctor(doctor_payload)
        assert doctor_resp.status_code == 201
        doctor_token = self.login_and_get_token(
            doctor_payload["email"], doctor_payload["password"]
        )

        pre_links = (
            self.db.query(DoctorPatientAssociation)
            .filter(DoctorPatientAssociation.doctor_email == doctor_payload["email"])
            .count()
        )
        assert pre_links == 1

        # Act: delete doctor
        delete_resp = self.client.delete(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(doctor_token),
        )

        # Assert
        assert delete_resp.status_code == 204
        assert self.db.get(Doctor, doctor_payload["email"]) is None
        # Patient survives and association is gone
        assert self.db.get(Patient, patient_payload["email"]) is not None
        assert (
            self.db.query(DoctorPatientAssociation)
            .filter(DoctorPatientAssociation.doctor_email == doctor_payload["email"])
            .count()
            == 0
        )

    def test_delete_question_clears_answers(self):
        # Arrange: patient with answered question
        admin = self.create_admin()
        admin_token = self.login_and_get_token(admin.email, self.default_password)
        question_id = self._create_question(admin_token)

        patient_payload = self.make_patient_payload()
        patient_resp = self.register_patient(patient_payload)
        assert patient_resp.status_code == 201

        patient_model = self.db.get(Patient, patient_payload["email"])
        question_model = self.db.get(Question, uuid.UUID(question_id))
        assert patient_model and question_model
        patient_model.add_answered_questions({question_model}, answered_at=datetime.now(timezone.utc))
        self.db.flush()

        # Act: delete question as admin
        delete_resp = self.client.delete(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(admin_token),
            query_string={"id": question_id},
        )

        # Assert
        assert delete_resp.status_code == 204
        assert self.db.get(Question, uuid.UUID(question_id)) is None
        assert (
            self.db.query(QuestionAnsweredAssociation)
            .filter(QuestionAnsweredAssociation.question_id == uuid.UUID(question_id))
            .count()
            == 0
        )

    def test_patch_patient_with_doctor_links(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)

        patient_payload = self.make_patient_payload(doctors=[doctor_payload["email"]])
        self.register_patient(patient_payload)
        patient_token = self.login_and_get_token(
            patient_payload["email"], patient_payload["password"]
        )

        patch_resp = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(patient_token),
            json={"surname": "UpdatedSurname"},
        )

        assert patch_resp.status_code == 200
        assert patch_resp.get_json()["surname"] == "UpdatedSurname"
        assert (
            self.db.query(DoctorPatientAssociation)
            .filter(DoctorPatientAssociation.patient_email == patient_payload["email"])
            .count()
            == 1
        )

    def test_patch_doctor_with_patient_links(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)

        doctor_payload = self.make_doctor_payload(patients=[patient_payload["email"]])
        self.register_doctor(doctor_payload)
        doctor_token = self.login_and_get_token(
            doctor_payload["email"], doctor_payload["password"]
        )

        patch_resp = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(doctor_token),
            json={"surname": "UpdatedDoctor"},
        )

        assert patch_resp.status_code == 200
        assert patch_resp.get_json()["surname"] == "UpdatedDoctor"
        assert (
            self.db.query(DoctorPatientAssociation)
            .filter(DoctorPatientAssociation.doctor_email == doctor_payload["email"])
            .count()
            == 1
        )
