from tests.base_test import BaseTest


class TestUserRegister(BaseTest):
    def test_register_patient_returns_user(self):
        doctor_user = self.create_doctor_model()
        payload = self.make_patient_payload(doctors=[doctor_user.email])

        response = self.register_patient(payload)

        assert response.status_code == 201
        body = response.get_json()
        assert body["email"] == payload["email"]
        assert body["name"] == payload["name"]
        assert body["role"]["doctors"] == [doctor_user.email]

    def test_register_doctor_returns_user(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        payload = self.make_doctor_payload(patients=[patient_payload["email"]])

        response = self.register_doctor(payload)

        assert response.status_code == 201
        body = response.get_json()
        assert body["email"] == payload["email"]
        assert body["role"]["patients"] == [patient_payload["email"]]

    def test_register_patient_with_unknown_doctor_returns_404(self):
        payload = self.make_patient_payload(doctors=["missing@nowhere.com"])

        response = self.register_patient(payload)

        assert response.status_code == 404

    def test_register_doctor_with_unknown_patient_returns_404(self):
        payload = self.make_doctor_payload(patients=["missing@nowhere.com"])

        response = self.register_doctor(payload)

        assert response.status_code == 404

    def test_register_patient_weak_password_returns_422(self):
        payload = self.make_patient_payload(password="weak")

        response = self.register_patient(payload)

        assert response.status_code == 422

    def test_register_patient_with_long_name_returns_422(self):
        payload = self.make_patient_payload(name="x" * 81)

        response = self.register_patient(payload)

        assert response.status_code == 422

    def test_register_patient_duplicate_email_returns_400(self):
        payload = self.make_patient_payload()

        first_response = self.register_patient(payload)
        assert first_response.status_code == 201

        duplicate_response = self.register_patient(payload)

        assert duplicate_response.status_code == 400

    def test_register_patient_age_out_of_range_returns_422_with_message(self):
        payload = self.make_patient_payload(age=130)

        response = self.register_patient(payload)

        assert response.status_code == 422
        body = response.get_json() or {}
        assert "L'edat del pacient ha d'estar entre 0 i 120 anys." in body.get("message", "")
