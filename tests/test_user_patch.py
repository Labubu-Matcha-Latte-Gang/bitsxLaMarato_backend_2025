from tests.base_test import BaseTest


class TestUserPatch(BaseTest):
    def test_patch_without_body_returns_current_user(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["email"] == patient_payload["email"]

    def test_patch_patient_can_replace_doctors(self):
        doctor_one = self.create_doctor_model()
        doctor_two = self.create_doctor_model()
        patient_payload = self.make_patient_payload(doctors=[doctor_one.email])
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"doctors": [doctor_two.email]},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["role"]["doctors"] == [doctor_two.email]

    def test_patch_patient_can_clear_doctors(self):
        doctor_one = self.create_doctor_model()
        patient_payload = self.make_patient_payload(doctors=[doctor_one.email])
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"doctors": []},
        )

        assert response.status_code == 200
        assert response.get_json()["role"]["doctors"] == []

    def test_patch_doctor_can_replace_patients(self):
        patient_one = self.create_patient_model()
        patient_two = self.create_patient_model()
        doctor_payload = self.make_doctor_payload(patients=[patient_one.email])
        self.register_doctor(doctor_payload)
        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"patients": [patient_two.email]},
        )

        assert response.status_code == 200
        assert response.get_json()["role"]["patients"] == [patient_two.email]

    def test_patch_doctor_can_clear_patients(self):
        patient_one = self.create_patient_model()
        doctor_payload = self.make_doctor_payload(patients=[patient_one.email])
        self.register_doctor(doctor_payload)
        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"patients": []},
        )

        assert response.status_code == 200
        assert response.get_json()["role"]["patients"] == []

    def test_patch_with_weak_password_returns_422(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"password": "weak"},
        )

        assert response.status_code == 422

    def test_patch_with_unknown_related_user_returns_404(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"doctors": ["missing@nowhere.com"]},
        )

        assert response.status_code == 404

    def test_patch_for_missing_user_returns_404(self):
        token = self.generate_token("ghost@example.com")

        response = self.client.patch(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
            json={"name": "Ghost"},
        )

        assert response.status_code == 404
