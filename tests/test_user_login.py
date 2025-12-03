from tests.base_test import BaseTest


class TestUserLogin(BaseTest):
    def test_login_returns_token(self):
        payload = self.make_patient_payload()
        self.register_patient(payload)

        response = self.login(payload["email"], payload["password"])

        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data is not None
        assert "access_token" in response_data
        assert isinstance(response_data["access_token"], str)
        assert len(response_data["access_token"]) > 0

    def test_login_with_wrong_password_returns_401(self):
        payload = self.make_patient_payload()
        self.register_patient(payload)

        response = self.login(payload["email"], "WrongPass1")

        assert response.status_code == 401

    def test_login_with_missing_email_returns_422(self):
        response = self.client.post(f"{self.api_prefix}/user/login", json={"password": "TestPass1"})
        
        assert response.status_code == 422

    def test_login_with_missing_password_returns_422(self):
        response = self.client.post(f"{self.api_prefix}/user/login", json={"email": "test@example.com"})
        
        assert response.status_code == 422

    def test_login_with_nonexistent_user_returns_401(self):
        response = self.login("nonexistent@example.com", "TestPass1")
        
        assert response.status_code == 401

    def test_login_with_empty_payload_returns_422(self):
        response = self.client.post(f"{self.api_prefix}/user/login", json={})
        
        assert response.status_code == 422

    def test_login_with_invalid_email_format_returns_422(self):
        response = self.client.post(f"{self.api_prefix}/user/login", json={
            "email": "invalid-email",
            "password": "TestPass1"
        })
        
        assert response.status_code == 422
