from tests.base_test import BaseTest


class TestUserPut(BaseTest):
    def test_put_updates_patient_and_clears_doctors(self):
        doctor_user = self.create_doctor_model()
        patient_payload = self.make_patient_payload(doctors=[doctor_user.email])
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        update_payload = {
            "name": "Updated",
            "surname": "Patient",
            "doctors": [],
        }

        response = self.client.put(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json=update_payload,
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["name"] == "Updated"
        assert body["role"]["doctors"] == []

    def test_put_updates_doctor_and_clears_patients(self):
        patient_user = self.create_patient_model()
        doctor_payload = self.make_doctor_payload(patients=[patient_user.email])
        self.register_doctor(doctor_payload)
        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        update_payload = {
            "name": "Updated",
            "surname": "Doctor",
            "patients": [],
        }

        response = self.client.put(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json=update_payload,
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["name"] == "Updated"
        assert body["role"]["patients"] == []

    def test_put_with_weak_password_returns_422(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.put(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"name": "Test", "surname": "User", "password": "weak"},
        )

        assert response.status_code == 422

    def test_put_with_unknown_related_user_returns_404(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.put(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"name": "Test", "surname": "User", "doctors": ["missing@nowhere.com"]},
        )

        assert response.status_code == 404

    def test_put_for_missing_user_returns_404(self):
        token = self.generate_token("ghost@example.com")

        response = self.client.put(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"name": "Ghost", "surname": "User"},
        )

        assert response.status_code == 404
