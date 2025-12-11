from tests.base_test import BaseTest


class TestDoctorPatientSearch(BaseTest):
    def test_doctor_can_search_assigned_patients_by_partial_name(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)
        patient_payload = self.make_patient_payload(
            name="Marta",
            surname="Garcia",
            doctors=[doctor_payload["email"]],
        )
        self.register_patient(patient_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.get(
            f"{self.api_prefix}/user/doctor/patients/search?q=GAR",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert body.get("query") == "GAR"
        emails = [item["email"] for item in body.get("results", [])]
        assert patient_payload["email"] in emails

    def test_doctor_only_sees_assigned_patients(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)

        assigned_patient = self.make_patient_payload(
            name="Carlos",
            surname="Martinez",
            doctors=[doctor_payload["email"]],
        )
        self.register_patient(assigned_patient)

        other_patient = self.make_patient_payload(
            name="Carla",
            surname="Martinez",
            doctors=[],
        )
        self.register_patient(other_patient)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.get(
            f"{self.api_prefix}/user/doctor/patients/search?q=mart",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        emails = [item["email"] for item in body.get("results", [])]
        assert assigned_patient["email"] in emails
        assert other_patient["email"] not in emails

    def test_patient_cannot_access_doctor_search(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)

        patient_payload = self.make_patient_payload(doctors=[doctor_payload["email"]])
        self.register_patient(patient_payload)

        patient_token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])
        response = self.client.get(
            f"{self.api_prefix}/user/doctor/patients/search?q=doe",
            headers=self.auth_headers(patient_token),
        )

        assert response.status_code == 403
