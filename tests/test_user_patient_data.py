from tests.base_test import BaseTest


class TestUserPatientData(BaseTest):
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
