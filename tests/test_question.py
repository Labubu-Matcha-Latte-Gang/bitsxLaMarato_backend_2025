from __future__ import annotations

import uuid

from helpers.enums.question_types import QuestionType
from tests.base_test import BaseTest


class TestQuestionResource(BaseTest):
    def _make_question_payload(self, **overrides) -> dict:
        return {
            "text": overrides.get("text", f"Pregunta de prova {uuid.uuid4().hex[:8]}"),
            "question_type": overrides.get("question_type", QuestionType.CONCENTRATION.value),
            "difficulty": overrides.get("difficulty", 2.5),
        }

    def get_admin_token(self) -> str:
        admin_user = self.create_admin()
        return self.login_and_get_token(admin_user.email, self.default_password)

    def _create_questions(self, count: int = 1, token: str | None = None):
        token = token or self.get_admin_token()
        payload = {
            "questions": [
                self._make_question_payload(text=f"Pregunta {i} {uuid.uuid4().hex[:8]}") for i in range(count)
            ]
        }
        return self.client.post(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            json=payload,
        )

    def test_create_and_get_questions(self):
        token = self.get_admin_token()
        baseline_resp = self.client.get(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
        )
        baseline = baseline_resp.get_json() or []
        create_resp = self._create_questions(count=2, token=token)
        assert create_resp.status_code == 201
        created = create_resp.get_json()
        assert len(created) == 2
        created_ids = {q["id"] for q in created}

        list_resp = self.client.get(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
        )
        assert list_resp.status_code == 200
        listed = list_resp.get_json() or []
        listed_ids = {q["id"] for q in listed}
        assert created_ids.issubset(listed_ids)
        assert len(listed) >= len(baseline)

    def test_filters_by_id_and_ranges(self):
        token = self.get_admin_token()
        create_resp = self._create_questions(count=3, token=token)
        body = create_resp.get_json()
        first_id = body[0]["id"]

        # By id
        get_resp = self.client.get(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            query_string={"id": first_id},
        )
        assert get_resp.status_code == 200
        data = get_resp.get_json()
        assert len(data) == 1
        assert data[0]["id"] == first_id

        # By difficulty range
        range_resp = self.client.get(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            query_string={"difficulty_min": 0, "difficulty_max": 2.6},
        )
        assert range_resp.status_code == 200
        ranged = range_resp.get_json()
        assert len(ranged) >= 1
        assert all(q["difficulty"] <= 2.6 for q in ranged)

    def test_put_updates_question(self):
        token = self.get_admin_token()
        create_resp = self._create_questions(count=1, token=token)
        question = create_resp.get_json()[0]

        update_payload = self._make_question_payload(
            text=f"Pregunta actualitzada {uuid.uuid4().hex[:8]}",
            difficulty=3.0,
        )
        put_resp = self.client.put(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            query_string={"id": question["id"]},
            json=update_payload,
        )
        assert put_resp.status_code == 200
        updated = put_resp.get_json()
        assert updated["text"] == update_payload["text"]
        assert updated["difficulty"] == 3.0

    def test_patch_updates_subset(self):
        token = self.get_admin_token()
        create_resp = self._create_questions(count=1, token=token)
        question = create_resp.get_json()[0]

        new_text = f"Nou text {uuid.uuid4().hex[:8]}"
        patch_resp = self.client.patch(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            query_string={"id": question["id"]},
            json={"text": new_text},
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.get_json()
        assert patched["text"] == new_text

    def test_delete_question(self):
        token = self.get_admin_token()
        create_resp = self._create_questions(count=1, token=token)
        question = create_resp.get_json()[0]

        del_resp = self.client.delete(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            query_string={"id": question["id"]},
        )
        assert del_resp.status_code == 204

        # Ensure it is gone
        get_resp = self.client.get(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            query_string={"id": question["id"]},
        )
        assert get_resp.status_code == 404

    def test_patient_cannot_access_admin_endpoints(self):
        patient_user = self.create_patient_model()
        token = self.generate_token(patient_user.email)

        resp = self.client.get(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
        )
        assert resp.status_code == 403

    def test_daily_question_for_patient(self):
        patient_user = self.create_patient_model()
        token = self.generate_token(patient_user.email)
        self._create_questions(count=2)  # create as admin

        resp = self.client.get(
            f"{self.api_prefix}/question/daily",
            headers=self.auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["id"]
        assert body["text"]

    def test_create_duplicate_text_returns_422_with_message(self):
        token = self.get_admin_token()
        unique_text = f"Enunciat únic {uuid.uuid4().hex[:8]}"
        payload = {"questions": [self._make_question_payload(text=unique_text)]}
        first = self.client.post(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            json=payload,
        )
        assert first.status_code == 201

        duplicate = self.client.post(
            f"{self.api_prefix}/question",
            headers=self.auth_headers(token),
            json=payload,
        )
        assert duplicate.status_code == 422
        body = duplicate.get_json() or {}
        assert "Ja existeix una pregunta amb aquest enunciat." in body.get("message", "")
