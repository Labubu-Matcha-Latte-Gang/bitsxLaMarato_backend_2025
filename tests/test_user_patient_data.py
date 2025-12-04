import base64
from uuid import uuid4

from application.container import ServiceFactory
from helpers.enums.question_types import QuestionType
from tests.base_test import BaseTest


class TestUserPatientData(BaseTest):
    def _seed_score_for_patient(self, patient_email: str) -> None:
        """
        Create a simple activity and register a score so the patient payload
        includes graph data.
        """
        factory = ServiceFactory.get_instance(session=self.db, refresh=True)
        activity_service = factory.build_activity_service()
        activity = activity_service.create_activities(
            [
                {
                    "title": f"Speed test {uuid4().hex[:8]}",
                    "description": "Quick check",
                    "activity_type": QuestionType.SPEED,
                    "difficulty": 1.0,
                }
            ]
        )[0]
        user_service = factory.build_user_service()
        patient = user_service.get_user(patient_email)
        score_service = factory.build_score_service()
        score_service.complete_activity(
            patient=patient,
            activity=activity,
            score_value=8.0,
            seconds_to_finish=42.0,
        )

    def test_admin_can_get_patient_data(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        admin_user = self.create_admin()
        admin_token = self.login_and_get_token(admin_user.email, self.default_password)

        response = self.client.get(
            f"{self.api_prefix}/user/{patient_payload['email']}",
            headers=self.auth_headers(admin_token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["patient"]["email"] == patient_payload["email"]
        assert "graph_files" in body

    def test_patient_data_includes_graph_fragment(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        self._seed_score_for_patient(patient_payload["email"])
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user/{patient_payload['email']}",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        graphs = body.get("graph_files", [])
        assert len(graphs) == 1  # one per activity type
        graph_file = graphs[0]
        assert graph_file["content_type"] == "text/html"
        decoded = base64.b64decode(graph_file["content"]).decode("utf-8")
        assert decoded.startswith("<div id=")
        assert "Plotly.newPlot" in decoded
        assert "<html" not in decoded.lower()

    def test_assigned_doctor_can_get_patient_data(self):
        doctor_user = self.create_doctor_model()
        patient_payload = self.make_patient_payload(doctors=[doctor_user.email])
        self.register_patient(patient_payload)
        doctor_token = self.login_and_get_token(doctor_user.email, self.default_password)

        response = self.client.get(
            f"{self.api_prefix}/user/{patient_payload['email']}",
            headers=self.auth_headers(doctor_token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["patient"]["email"] == patient_payload["email"]
        assert "graph_files" in body

    def test_unassigned_doctor_gets_403(self):
        doctor_user = self.create_doctor_model()
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        doctor_token = self.login_and_get_token(doctor_user.email, self.default_password)

        response = self.client.get(
            f"{self.api_prefix}/user/{patient_payload['email']}",
            headers=self.auth_headers(doctor_token),
        )

        assert response.status_code == 403

    def test_patient_can_get_own_data(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user/{patient_payload['email']}",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["patient"]["email"] == patient_payload["email"]
        assert "graph_files" in body

    def test_other_patient_gets_403(self):
        patient_one = self.make_patient_payload()
        self.register_patient(patient_one)
        patient_two = self.make_patient_payload()
        self.register_patient(patient_two)
        token = self.login_and_get_token(patient_two["email"], patient_two["password"])

        response = self.client.get(
            f"{self.api_prefix}/user/{patient_one['email']}",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 403

    def test_missing_patient_returns_404(self):
        admin_user = self.create_admin()
        admin_token = self.login_and_get_token(admin_user.email, self.default_password)

        response = self.client.get(
            f"{self.api_prefix}/user/missing@example.com",
            headers=self.auth_headers(admin_token),
        )

        assert response.status_code == 404
