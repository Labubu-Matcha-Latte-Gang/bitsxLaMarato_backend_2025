from application.container import ServiceFactory
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

    def test_doctor_can_assign_multiple_patients(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)

        patient_one = self.make_patient_payload(name="Alice", surname="Nova")
        patient_two = self.make_patient_payload(name="Albert", surname="Nova")
        self.register_patient(patient_one)
        self.register_patient(patient_two)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/assign",
            json={"patients": [patient_one["email"], patient_two["email"]]},
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload is not None
        patients = payload.get("role", {}).get("patients", [])
        assert patient_one["email"] in patients
        assert patient_two["email"] in patients

        factory = ServiceFactory.get_instance(refresh=True)
        patient_service = factory.build_patient_service()
        stored_patient = patient_service.get_patient(patient_one["email"])
        assert doctor_payload["email"] in stored_patient.doctor_emails

    def test_doctor_can_remove_multiple_patients(self):
        patient_one = self.make_patient_payload()
        patient_two = self.make_patient_payload()
        doctor_payload = self.make_doctor_payload(patients=[patient_one["email"], patient_two["email"]])

        self.register_patient(patient_one)
        self.register_patient(patient_two)
        self.register_doctor(doctor_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/unassign",
            json={"patients": [patient_one["email"], patient_two["email"]]},
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload is not None
        patients = payload.get("role", {}).get("patients", [])
        assert patient_one["email"] not in patients
        assert patient_two["email"] not in patients

        factory = ServiceFactory.get_instance(refresh=True)
        patient_service = factory.build_patient_service()
        refreshed_patient = patient_service.get_patient(patient_one["email"])
        assert doctor_payload["email"] not in refreshed_patient.doctor_emails

    def test_assigning_nonexistent_patient_returns_404(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)
        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/assign",
            json={"patients": ["ghost@example.com"]},
            headers=self.auth_headers(token),
        )

        assert response.status_code == 404

    def test_assigning_empty_patient_list_returns_404(self):
        """
        Edge case: assigning an empty patient list should return 404
        with an appropriate error message.
        """
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)
        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/assign",
            json={"patients": []},
            headers=self.auth_headers(token),
        )

        assert response.status_code == 404
        body = response.get_json()
        assert body is not None
        assert "message" in body

    def test_assigning_duplicate_patient_emails_deduplicates(self):
        """
        Edge case: assigning duplicate patient emails in the same request
        should automatically deduplicate and assign the patient only once.
        """
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)

        patient_payload = self.make_patient_payload(name="Elena", surname="Rius")
        self.register_patient(patient_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/assign",
            json={"patients": [patient_payload["email"], patient_payload["email"], patient_payload["email"]]},
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload is not None
        patients = payload.get("role", {}).get("patients", [])
        # Patient should appear only once despite being in the list three times
        assert patients.count(patient_payload["email"]) == 1

    def test_assigning_already_assigned_patient_is_idempotent(self):
        """
        Edge case: attempting to assign a patient that is already assigned
        should succeed without error (idempotent operation).
        """
        patient_payload = self.make_patient_payload(name="Marc", surname="Puig")
        self.register_patient(patient_payload)

        doctor_payload = self.make_doctor_payload(patients=[patient_payload["email"]])
        self.register_doctor(doctor_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        # Try to assign the same patient again
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/assign",
            json={"patients": [patient_payload["email"]]},
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload is not None
        patients = payload.get("role", {}).get("patients", [])
        # Patient should still appear only once
        assert patients.count(patient_payload["email"]) == 1

    def test_removing_unassigned_patient_succeeds_silently(self):
        """
        Edge case: removing a patient that is not currently assigned
        should succeed without error (graceful handling).
        """
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)

        # Create a patient but don't assign them to the doctor
        patient_payload = self.make_patient_payload(name="Laura", surname="Vila")
        self.register_patient(patient_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/unassign",
            json={"patients": [patient_payload["email"]]},
            headers=self.auth_headers(token),
        )

        # Should succeed even though patient was never assigned
        assert response.status_code == 200
        payload = response.get_json()
        assert payload is not None
        patients = payload.get("role", {}).get("patients", [])
        assert patient_payload["email"] not in patients
