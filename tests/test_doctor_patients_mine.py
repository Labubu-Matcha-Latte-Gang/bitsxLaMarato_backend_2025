from application.container import ServiceFactory
from tests.base_test import BaseTest


class TestDoctorMyPatients(BaseTest):
    """
    Comprehensive test suite for the /doctor/patients/mine endpoint.
    
    This endpoint allows doctors to retrieve the list of patients
    they are associated with.
    """

    def test_doctor_retrieves_assigned_patients_successfully(self):
        """
        Happy path: A doctor with assigned patients can retrieve their list.
        """
        # Create patients first
        patient_one = self.make_patient_payload(name="Anna", surname="Garcia")
        patient_two = self.make_patient_payload(name="Marc", surname="Lopez")
        self.register_patient(patient_one)
        self.register_patient(patient_two)

        # Create doctor with assigned patients
        doctor_payload = self.make_doctor_payload(
            patients=[patient_one["email"], patient_two["email"]]
        )
        self.register_doctor(doctor_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert isinstance(body, list)
        assert len(body) == 2

        # Verify patient emails are in the response
        patient_emails = [patient["email"] for patient in body]
        assert patient_one["email"] in patient_emails
        assert patient_two["email"] in patient_emails

        # Verify response structure contains expected fields
        for patient in body:
            assert "email" in patient
            assert "name" in patient
            assert "surname" in patient
            assert "role" in patient
            # Verify that doctors field is removed from nested role
            assert "doctors" not in patient["role"]

    def test_doctor_with_no_patients_returns_empty_list(self):
        """
        Edge case: A doctor with no assigned patients receives an empty list.
        """
        doctor_payload = self.make_doctor_payload(patients=[])
        self.register_doctor(doctor_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert isinstance(body, list)
        assert len(body) == 0

    def test_missing_jwt_returns_401(self):
        """
        Authorization test: Request without JWT returns 401 Unauthorized.
        """
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
        )

        assert response.status_code == 401

    def test_invalid_jwt_returns_401(self):
        """
        Authorization test: Request with invalid JWT returns 401 Unauthorized.
        """
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers("invalid.jwt.token"),
        )

        assert response.status_code == 401

    def test_patient_cannot_access_endpoint(self):
        """
        Authorization test: A patient cannot access the doctor endpoint.
        Should return 403 Forbidden.
        """
        # Create a doctor first
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)

        # Create a patient
        patient_payload = self.make_patient_payload(doctors=[doctor_payload["email"]])
        self.register_patient(patient_payload)

        # Try to access endpoint as patient
        patient_token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(patient_token),
        )

        assert response.status_code == 403

    def test_admin_cannot_access_endpoint(self):
        """
        Authorization test: An admin cannot access the doctor endpoint.
        Should return 403 Forbidden.
        """
        admin = self.create_admin()

        admin_token = self.generate_token(admin.email)
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(admin_token),
        )

        assert response.status_code == 403

    def test_doctor_retrieves_patients_with_normalized_response(self):
        """
        Response normalization: Verify that the response properly normalizes
        patient data by removing nested 'doctors' field from role.
        """
        # Create multiple patients
        patient_one = self.make_patient_payload(name="Elena", surname="Gomez")
        patient_two = self.make_patient_payload(name="David", surname="Fernandez")
        patient_three = self.make_patient_payload(name="Laura", surname="Martinez")
        self.register_patient(patient_one)
        self.register_patient(patient_two)
        self.register_patient(patient_three)

        # Create doctor with all patients assigned
        doctor_payload = self.make_doctor_payload(
            patients=[patient_one["email"], patient_two["email"], patient_three["email"]]
        )
        self.register_doctor(doctor_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert len(body) == 3

        # Verify normalization for each patient
        for patient in body:
            assert "role" in patient
            # The key assertion: doctors field should be removed
            assert "doctors" not in patient["role"], "Response should not include 'doctors' field in patient role"
            # Verify other patient role fields are still present
            assert "ailments" in patient["role"] or patient["role"].get("ailments") is None
            assert "treatments" in patient["role"] or patient["role"].get("treatments") is None

    def test_multiple_doctors_sharing_patients(self):
        """
        Edge case: When multiple doctors share patients, each doctor
        should only see their own associated patients.
        """
        # Create patients
        patient_one = self.make_patient_payload(name="Shared", surname="Patient1")
        patient_two = self.make_patient_payload(name="Exclusive", surname="Patient2")
        self.register_patient(patient_one)
        self.register_patient(patient_two)

        # Doctor 1 has both patients
        doctor_one = self.make_doctor_payload(
            email=self.unique_email("doctor1"),
            patients=[patient_one["email"], patient_two["email"]]
        )
        self.register_doctor(doctor_one)

        # Doctor 2 has only patient_one
        doctor_two = self.make_doctor_payload(
            email=self.unique_email("doctor2"),
            patients=[patient_one["email"]]
        )
        self.register_doctor(doctor_two)

        # Doctor 1 should see both patients
        token_one = self.login_and_get_token(doctor_one["email"], doctor_one["password"])
        response_one = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token_one),
        )
        assert response_one.status_code == 200
        body_one = response_one.get_json()
        assert len(body_one) == 2
        emails_one = [p["email"] for p in body_one]
        assert patient_one["email"] in emails_one
        assert patient_two["email"] in emails_one

        # Doctor 2 should see only patient_one
        token_two = self.login_and_get_token(doctor_two["email"], doctor_two["password"])
        response_two = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token_two),
        )
        assert response_two.status_code == 200
        body_two = response_two.get_json()
        assert len(body_two) == 1
        emails_two = [p["email"] for p in body_two]
        assert patient_one["email"] in emails_two
        assert patient_two["email"] not in emails_two

    def test_doctor_retrieves_patients_after_assignment(self):
        """
        Integration test: Verify that after assigning patients via the
        /assign endpoint, those patients appear in the /mine endpoint.
        """
        # Create doctor with no patients
        doctor_payload = self.make_doctor_payload(patients=[])
        self.register_doctor(doctor_payload)

        # Create patients
        patient_one = self.make_patient_payload(name="New", surname="Patient1")
        patient_two = self.make_patient_payload(name="New", surname="Patient2")
        self.register_patient(patient_one)
        self.register_patient(patient_two)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        # Initially, doctor should have no patients
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 0

        # Assign patients
        assign_response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/assign",
            json={"patients": [patient_one["email"], patient_two["email"]]},
            headers=self.auth_headers(token),
        )
        assert assign_response.status_code == 200

        # Now, doctor should see the assigned patients
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 2
        patient_emails = [p["email"] for p in body]
        assert patient_one["email"] in patient_emails
        assert patient_two["email"] in patient_emails

    def test_doctor_retrieves_patients_after_unassignment(self):
        """
        Integration test: Verify that after unassigning patients via the
        /unassign endpoint, those patients no longer appear in the /mine endpoint.
        """
        # Create patients
        patient_one = self.make_patient_payload(name="ToRemove", surname="Patient1")
        patient_two = self.make_patient_payload(name="ToKeep", surname="Patient2")
        self.register_patient(patient_one)
        self.register_patient(patient_two)

        # Create doctor with both patients
        doctor_payload = self.make_doctor_payload(
            patients=[patient_one["email"], patient_two["email"]]
        )
        self.register_doctor(doctor_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        # Verify doctor initially has both patients
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 2

        # Unassign patient_one
        unassign_response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/unassign",
            json={"patients": [patient_one["email"]]},
            headers=self.auth_headers(token),
        )
        assert unassign_response.status_code == 200

        # Now, doctor should only see patient_two
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 1
        assert body[0]["email"] == patient_two["email"]

    def test_response_includes_patient_role_data(self):
        """
        Data integrity test: Verify that the response includes complete
        patient role data (age, height, weight, etc.).
        """
        # Create patient with specific data
        patient_payload = self.make_patient_payload(
            name="Complete",
            surname="DataPatient",
            age=45,
            height_cm=175.5,
            weight_kg=70.2,
            ailments="Diabetes",
            treatments="Insulina"
        )
        self.register_patient(patient_payload)

        # Create doctor with patient
        doctor_payload = self.make_doctor_payload(patients=[patient_payload["email"]])
        self.register_doctor(doctor_payload)

        token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])
        response = self.client.post(
            f"{self.api_prefix}/user/doctor/patients/mine",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 1

        patient = body[0]
        assert patient["email"] == patient_payload["email"]
        assert patient["name"] == patient_payload["name"]
        assert patient["surname"] == patient_payload["surname"]

        # Verify role data is present
        role = patient["role"]
        assert role["age"] == patient_payload["age"]
        assert role["height_cm"] == patient_payload["height_cm"]
        assert role["weight_kg"] == patient_payload["weight_kg"]
        assert role["ailments"] == patient_payload["ailments"]
        assert role["treatments"] == patient_payload["treatments"]
