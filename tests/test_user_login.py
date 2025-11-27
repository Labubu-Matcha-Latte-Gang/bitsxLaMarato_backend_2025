from tests.base_test import BaseTest


class TestUserLogin(BaseTest):
    def test_login_returns_token(self):
        payload = self.make_patient_payload()
        self.register_patient(payload)

        response = self.login(payload["email"], payload["password"])

        assert response.status_code == 200
        assert "access_token" in (response.get_json() or {})

    def test_login_with_wrong_password_returns_401(self):
        payload = self.make_patient_payload()
        self.register_patient(payload)

        response = self.login(payload["email"], "WrongPass1")

        assert response.status_code == 401
