from tests.base_test import BaseTest


class TestUserMe(BaseTest):
    def test_get_me_returns_patient_profile(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user", headers=self.auth_headers(token)
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["email"] == patient_payload["email"]
        assert body["role"]["gender"] == patient_payload["gender"]

    def test_get_me_returns_doctor_profile(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)
        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user", headers=self.auth_headers(token)
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["email"] == doctor_payload["email"]
        assert "patients" in body["role"]

    def test_get_me_returns_admin_profile(self):
        admin_user = self.create_admin()
        token = self.login_and_get_token(admin_user.email, self.default_password)

        response = self.client.get(
            f"{self.api_prefix}/user", headers=self.auth_headers(token)
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["email"] == admin_user.email
        assert body["role"] == {}
