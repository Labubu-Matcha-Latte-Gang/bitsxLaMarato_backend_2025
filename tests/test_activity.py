from __future__ import annotations

import uuid

from helpers.enums.question_types import QuestionType
from models.score import Score
from tests.base_test import BaseTest


class TestActivityResource(BaseTest):
    def _make_activity_payload(self, **overrides) -> dict:
        return {
            "title": overrides.get("title", f"Activitat de prova {uuid.uuid4().hex[:8]}"),
            "description": overrides.get("description", "Descripcio de prova"),
            "activity_type": overrides.get("activity_type", QuestionType.CONCENTRATION.value),
            "difficulty": overrides.get("difficulty", 2.5),
        }

    def get_admin_token(self) -> str:
        admin_user = self.create_admin()
        return self.login_and_get_token(admin_user.email, self.default_password)

    def _create_activities(self, count: int = 1, token: str | None = None):
        token = token or self.get_admin_token()
        payload = {
            "activities": [
                self._make_activity_payload(title=f"Activitat {i} {uuid.uuid4().hex[:8]}") for i in range(count)
            ]
        }
        return self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json=payload,
        )

    def test_create_and_get_activities(self):
        token = self.get_admin_token()
        baseline_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
        )
        baseline = baseline_resp.get_json() or []
        create_resp = self._create_activities(count=2, token=token)
        assert create_resp.status_code == 201
        created = create_resp.get_json()
        assert len(created) == 2
        created_ids = {a["id"] for a in created}

        list_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
        )
        assert list_resp.status_code == 200
        listed = list_resp.get_json() or []
        listed_ids = {a["id"] for a in listed}
        assert created_ids.issubset(listed_ids)
        assert len(listed) >= len(baseline)

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

    def test_search_filters_by_partial_title_case_insensitive(self):
        token = self.get_admin_token()
        target_title = "Vamos a contar palabras"
        other_title = "Lista de compra semanal"

        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={
                "activities": [
                    self._make_activity_payload(title=target_title),
                    self._make_activity_payload(title=other_title),
                ]
            },
        )
        assert resp.status_code == 201

        search_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": "CONTAR"},
        )
        assert search_resp.status_code == 200
        results = search_resp.get_json() or []
        titles = {a["title"] for a in results}
        assert target_title in titles
        assert other_title not in titles

    def test_search_with_empty_string_returns_all_activities(self):
        token = self.get_admin_token()
        title_1 = "Primera activitat"
        title_2 = "Segona activitat"

        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={
                "activities": [
                    self._make_activity_payload(title=title_1),
                    self._make_activity_payload(title=title_2),
                ]
            },
        )
        assert resp.status_code == 201

        search_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": ""},
        )
        assert search_resp.status_code == 200
        results = search_resp.get_json() or []
        titles = {a["title"] for a in results}
        assert title_1 in titles
        assert title_2 in titles

    def test_search_with_whitespace_only_returns_all_activities(self):
        token = self.get_admin_token()
        title_1 = "Activitat amb espais"
        title_2 = "Una altra activitat"

        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={
                "activities": [
                    self._make_activity_payload(title=title_1),
                    self._make_activity_payload(title=title_2),
                ]
            },
        )
        assert resp.status_code == 201

        search_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": "   "},
        )
        assert search_resp.status_code == 200
        results = search_resp.get_json() or []
        titles = {a["title"] for a in results}
        assert title_1 in titles
        assert title_2 in titles

    def test_search_with_special_characters(self):
        token = self.get_admin_token()
        title_with_special = "Activitat #1: Números & símbols!"
        title_normal = "Activitat sense simbols"

        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={
                "activities": [
                    self._make_activity_payload(title=title_with_special),
                    self._make_activity_payload(title=title_normal),
                ]
            },
        )
        assert resp.status_code == 201

        search_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": "#1"},
        )
        assert search_resp.status_code == 200
        results = search_resp.get_json() or []
        titles = {a["title"] for a in results}
        assert title_with_special in titles
        assert title_normal not in titles

    def test_search_combined_with_difficulty_filter(self):
        token = self.get_admin_token()
        title_easy = "Buscar paraules fàcils"
        title_hard = "Buscar paraules difícils"

        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={
                "activities": [
                    self._make_activity_payload(title=title_easy, difficulty=1.5),
                    self._make_activity_payload(title=title_hard, difficulty=4.5),
                ]
            },
        )
        assert resp.status_code == 201

        search_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": "paraules", "difficulty_min": 4.0},
        )
        assert search_resp.status_code == 200
        results = search_resp.get_json() or []
        titles = {a["title"] for a in results}
        assert title_hard in titles
        assert title_easy not in titles

    def test_search_that_matches_no_results(self):
        token = self.get_admin_token()
        title_1 = "Activitat de concentració"
        title_2 = "Exercici de memòria"

        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={
                "activities": [
                    self._make_activity_payload(title=title_1),
                    self._make_activity_payload(title=title_2),
                ]
            },
        )
        assert resp.status_code == 201

        search_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": "xyznonexistent123"},
        )
        assert search_resp.status_code == 200
        results = search_resp.get_json() or []
        assert len(results) == 0

    def test_search_with_very_long_string(self):
        token = self.get_admin_token()
        title_short = "Activitat curta"
        title_long = "Activitat amb un títol molt llarg que conté moltes paraules diferents i conceptes"

        resp = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json={
                "activities": [
                    self._make_activity_payload(title=title_short),
                    self._make_activity_payload(title=title_long),
                ]
            },
        )
        assert resp.status_code == 201

        very_long_search = "a" * 500
        search_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": very_long_search},
        )
        assert search_resp.status_code == 200
        results = search_resp.get_json() or []
        assert len(results) == 0

        partial_long_search = "títol molt llarg"
        search_resp_2 = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"search": partial_long_search},
        )
        assert search_resp_2.status_code == 200
        results_2 = search_resp_2.get_json() or []
        titles = {a["title"] for a in results_2}
        assert title_long in titles
        assert title_short not in titles

    def test_put_updates_activity(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=token)
        activity = create_resp.get_json()[0]

        update_payload = self._make_activity_payload(
            title=f"Activitat actualitzada {uuid.uuid4().hex[:8]}",
            difficulty=3.0,
        )
        put_resp = self.client.put(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": activity["id"]},
            json=update_payload,
        )
        assert put_resp.status_code == 200
        updated = put_resp.get_json()
        assert updated["title"] == update_payload["title"]
        assert updated["difficulty"] == 3.0

    def test_patch_updates_subset(self):
        token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=token)
        activity = create_resp.get_json()[0]

        new_title = f"Nou titol {uuid.uuid4().hex[:8]}"
        patch_resp = self.client.patch(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            query_string={"id": activity["id"]},
            json={"title": new_title},
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.get_json()
        assert patched["title"] == new_title

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

    def test_delete_activity_cascades_scores(self):
        admin_token = self.get_admin_token()
        create_resp = self._create_activities(count=1, token=admin_token)
        activity = create_resp.get_json()[0]

        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        patient_token = self.login_and_get_token(
            patient_payload["email"], patient_payload["password"]
        )

        complete_resp = self.client.post(
            f"{self.api_prefix}/activity/complete",
            headers=self.auth_headers(patient_token),
            json={
                "id": activity["id"],
                "score": 7.0,
                "seconds_to_finish": 15.0,
            },
        )
        assert complete_resp.status_code == 200

        activity_uuid = uuid.UUID(activity["id"])
        pre_delete_count = (
            self.db.query(Score).filter(Score.activity_id == activity_uuid).count()
        )
        assert pre_delete_count == 1

        del_resp = self.client.delete(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(admin_token),
            query_string={"id": activity["id"]},
        )
        assert del_resp.status_code == 204

        post_delete_count = (
            self.db.query(Score).filter(Score.activity_id == activity_uuid).count()
        )
        assert post_delete_count == 0

    def test_patient_can_get_activities(self):
        admin_token = self.get_admin_token()
        create_resp = self._create_activities(count=2, token=admin_token)
        assert create_resp.status_code == 201
        created = create_resp.get_json()
        created_ids = {a["id"] for a in created}

        patient_user = self.create_patient_model()
        patient_token = self.generate_token(patient_user.email)

        list_resp = self.client.get(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(patient_token),
        )
        assert list_resp.status_code == 200
        listed = list_resp.get_json() or []
        listed_ids = {a["id"] for a in listed}
        assert created_ids.issubset(listed_ids)

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

    def test_create_duplicate_title_returns_422_with_message(self):
        token = self.get_admin_token()
        unique_title = f"Títol únic {uuid.uuid4().hex[:8]}"
        payload = {"activities": [self._make_activity_payload(title=unique_title)]}
        first = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json=payload,
        )
        assert first.status_code == 201

        duplicate = self.client.post(
            f"{self.api_prefix}/activity",
            headers=self.auth_headers(token),
            json=payload,
        )
        assert duplicate.status_code == 422
        body = duplicate.get_json() or {}
        assert "Ja existeix una activitat amb aquest títol." in body.get("message", "")
