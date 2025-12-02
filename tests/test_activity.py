from __future__ import annotations

import uuid

from helpers.enums.question_types import QuestionType
from tests.base_test import BaseTest


class TestActivityResource(BaseTest):
    def _make_activity_payload(self, **overrides) -> dict:
        return {
            "title": overrides.get("title", "Activitat de prova"),
            "description": overrides.get("description", "Descripcio de prova"),
            "activity_type": overrides.get("activity_type", QuestionType.CONCENTRATION.value),
            "difficulty": overrides.get("difficulty", 2.5),
        }

    def get_admin_token(self) -> str:
        admin_user = self.create_admin()
        return self.login_and_get_token(admin_user.email, self.default_password)

    def _create_activities(self, count: int = 1, token: str | None = None):
        token = token or self.get_admin_token()
        payload = {"activities": [self._make_activity_payload(title=f"Activitat {i}") for i in range(count)]}
        return self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json=payload,
        )

    def test_create_and_get_activities(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=2, token=token)
        assert create_resp.status_code == 201
        created = create_resp.get_json()
        assert len(created) == 2

        list_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
        )
        assert list_resp.status_code == 200
        listed = list_resp.get_json()
        assert len(listed) == 2
        assert {a["title"] for a in listed} == {a["title"] for a in created}

    def test_filters_by_id_title_and_ranges(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=3, token=token)
        body = create_resp.get_json()
        first_id = body[0]["id"]
        first_title = body[0]["title"]

        get_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": first_id},
        )
        assert get_resp.status_code == 200
        data = get_resp.get_json()
        assert len(data) == 1
        assert data[0]["id"] == first_id

        title_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"title": first_title},
        )
        assert title_resp.status_code == 200
        titled = title_resp.get_json()
        assert len(titled) == 1
        assert titled[0]["title"] == first_title

        range_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"difficulty_min": 0, "difficulty_max": 2.6},
        )
        assert range_resp.status_code == 200
        ranged = range_resp.get_json()
        assert len(ranged) >= 1
        assert all(a["difficulty"] <= 2.6 for a in ranged)

    def test_put_updates_activity(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=token)
        activity = create_resp.get_json()[0]

        update_payload = self._make_activity_payload(title="Activitat actualitzada", difficulty=3.0)
        put_resp = self.client.put(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": activity["id"]},
            json=update_payload,
        )
        assert put_resp.status_code == 200
        updated = put_resp.get_json()
        assert updated["title"] == "Activitat actualitzada"
        assert updated["difficulty"] == 3.0

    def test_patch_updates_subset(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=token)
        activity = create_resp.get_json()[0]

        patch_resp = self.client.patch(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": activity["id"]},
            json={"title": "Nou titol"},
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.get_json()
        assert patched["title"] == "Nou titol"

    def test_patch_without_body_returns_400(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=token)
        activity = create_resp.get_json()[0]

        resp = self.client.patch(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": activity["id"]},
            json={},
        )
        assert resp.status_code == 400

    def test_delete_activity(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=token)
        activity = create_resp.get_json()[0]

        del_resp = self.client.delete(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": activity["id"]},
        )
        assert del_resp.status_code == 204

        get_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": activity["id"]},
        )
        assert get_resp.status_code == 404

    def test_patient_can_get_activities(self):
        admin_token = self.get_admin_token()
        create_resp = self._create_activities(count=2, token=admin_token)
        assert create_resp.status_code == 201
        created = create_resp.get_json()

        patient_user = self.create_patient_model()
        patient_token = self.generate_token(patient_user.email)

        list_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(patient_token),
        )
        assert list_resp.status_code == 200
        listed = list_resp.get_json()
        assert {a["title"] for a in listed} == {a["title"] for a in created}

        filtered_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(patient_token),
            query_string={"id": created[0]["id"]},
        )
        assert filtered_resp.status_code == 200
        filtered = filtered_resp.get_json()
        assert len(filtered) == 1
        assert filtered[0]["id"] == created[0]["id"]

    def test_patient_cannot_modify_activities(self):
        admin_token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=admin_token)
        activity = create_resp.get_json()[0]

        patient_user = self.create_patient_model()
        patient_token = self.generate_token(patient_user.email)

        post_resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(patient_token),
            json={"activities": [self._make_activity_payload()]},
        )
        assert post_resp.status_code == 403

        put_resp = self.client.put(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(patient_token),
            query_string={"id": activity["id"]},
            json=self._make_activity_payload(title="No hauria d'actualitzar"),
        )
        assert put_resp.status_code == 403

        patch_resp = self.client.patch(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(patient_token),
            query_string={"id": activity["id"]},
            json={"title": "No hauria de canviar"},
        )
        assert patch_resp.status_code == 403

        delete_resp = self.client.delete(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(patient_token),
            query_string={"id": activity["id"]},
        )
        assert delete_resp.status_code == 403

    def test_recommended_activity_for_patient(self):
        patient_user = self.create_patient_model()
        token = self.generate_token(patient_user.email)
        self._create_activities(count=2)  # create as admin

        resp = self.client.get(
            f"{self.api_prefix}/activity/recommended",
            headers=self.auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["id"]
        assert body["title"]

    def test_get_not_found_returns_404(self):
        token = self.get_admin_token()
        resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_create_validation_error_returns_422(self):
        token = self.get_admin_token()
        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={},
        )
        assert resp.status_code == 422
