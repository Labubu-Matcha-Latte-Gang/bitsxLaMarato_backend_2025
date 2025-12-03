from models.user import User
from tests.base_test import BaseTest


class TestUserDelete(BaseTest):
    def test_delete_removes_user(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.delete(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 204
        assert self.db.get(User, patient_payload["email"]) is None

    def test_delete_missing_user_returns_404(self):
        token = self.generate_token("ghost@example.com")

        response = self.client.delete(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 404
