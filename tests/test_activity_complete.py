import uuid

from helpers.enums.question_types import QuestionType
from tests.base_test import BaseTest
from application.container import ServiceFactory


class TestActivityComplete(BaseTest):
    def _create_activity(self):
        factory = ServiceFactory.get_instance(session=self.db, refresh=True)
        activity_service = factory.build_activity_service()
        activity = activity_service.create_activities(
            [
                {
                    "title": f"Activity {uuid.uuid4().hex[:6]}",
                    "description": "Desc",
                    "activity_type": QuestionType.SPEED,
                    "difficulty": 1.0,
                }
            ]
        )[0]
        return activity

    def _register_and_login_patient(self):
        payload = self.make_patient_payload()
        self.register_patient(payload)
        token = self.login_and_get_token(payload["email"], payload["password"])
        return payload["email"], token

    def test_patient_can_complete_activity(self):
        email, token = self._register_and_login_patient()
        activity = self._create_activity()

        response = self.client.post(
            f"{self.api_prefix}/activity/complete",
            headers=self.auth_headers(token),
            json={
                "id": str(activity.id),
                "score": 8.5,
                "seconds_to_finish": 120.3,
            },
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["patient"]["email"] == email
        assert body["activity"]["id"] == str(activity.id)
        assert body["score"] == 8.5
        assert body["seconds_to_finish"] == 120.3
        assert "completed_at" in body

    def test_activity_not_found_returns_404(self):
        _, token = self._register_and_login_patient()
        missing_id = uuid.uuid4()

        response = self.client.post(
            f"{self.api_prefix}/activity/complete",
            headers=self.auth_headers(token),
            json={
                "id": str(missing_id),
                "score": 5.0,
                "seconds_to_finish": 10.0,
            },
        )

        assert response.status_code == 404

    def test_requires_authentication(self):
        activity = self._create_activity()

        response = self.client.post(
            f"{self.api_prefix}/activity/complete",
            json={
                "id": str(activity.id),
                "score": 5.0,
                "seconds_to_finish": 10.0,
            },
        )

        assert response.status_code == 401

    def test_forbidden_for_non_patient(self):
        admin = self.create_admin()
        token = self.login_and_get_token(admin.email, self.default_password)
        activity = self._create_activity()

        response = self.client.post(
            f"{self.api_prefix}/activity/complete",
            headers=self.auth_headers(token),
            json={
                "id": str(activity.id),
                "score": 5.0,
                "seconds_to_finish": 10.0,
            },
        )

        assert response.status_code == 403

    def test_validation_error_returns_422(self):
        _, token = self._register_and_login_patient()

        response = self.client.post(
            f"{self.api_prefix}/activity/complete",
            headers=self.auth_headers(token),
            json={"seconds_to_finish": 10.0, "score": 5.0},  # missing id
        )

        assert response.status_code == 422

    def test_score_out_of_range_returns_500(self):
        _, token = self._register_and_login_patient()
        activity = self._create_activity()

        response = self.client.post(
            f"{self.api_prefix}/activity/complete",
            headers=self.auth_headers(token),
            json={
                "id": str(activity.id),
                "score": 12.0,  # violates check_score_range
                "seconds_to_finish": 10.0,
            },
        )

        assert response.status_code == 500
