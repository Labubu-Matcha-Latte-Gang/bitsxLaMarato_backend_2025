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


class TestUserTokenRefresh(BaseTest):
    def test_refresh_token_returns_new_token(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        original_token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user/login?hours_validity=2.5",
            headers=self.auth_headers(original_token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert "access_token" in body
        assert isinstance(body["access_token"], str)
        assert body["access_token"] != original_token

    def test_refresh_token_without_auth_header_returns_401(self):
        response = self.client.get(f"{self.api_prefix}/user/login")

        assert response.status_code == 401
        body = response.get_json()
        assert body is not None
        assert "msg" in body

    def test_refresh_token_with_invalid_token_returns_422(self):
        response = self.client.get(
            f"{self.api_prefix}/user/login",
            headers={"Authorization": "Bearer malformed.token.value"},
        )

        assert response.status_code == 422
        body = response.get_json()
        assert body is not None
        assert "msg" in body

    def test_refresh_token_with_nonexistent_user_returns_401(self):
        fake_token = self.generate_token("ghost@example.com")

        response = self.client.get(
            f"{self.api_prefix}/user/login",
            headers=self.auth_headers(fake_token),
        )

        assert response.status_code == 401
        body = response.get_json()
        assert body is not None
        assert body.get("message") == "Token d'autenticació no vàlid."

    def test_refresh_token_with_invalid_hours_validity_returns_422(self):
        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user/login?hours_validity=0.5",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 422

    def test_refresh_token_with_doctor_returns_new_token(self):
        doctor_payload = self.make_doctor_payload()
        self.register_doctor(doctor_payload)
        original_token = self.login_and_get_token(doctor_payload["email"], doctor_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user/login?hours_validity=2.5",
            headers=self.auth_headers(original_token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert "access_token" in body
        assert isinstance(body["access_token"], str)
        assert body["access_token"] != original_token
        new_token = body["access_token"]
        assert isinstance(new_token, str)
        assert new_token != original_token

    def test_refresh_token_without_hours_validity_uses_default(self):
        from datetime import datetime, timezone
        from flask_jwt_extended import decode_token

        patient_payload = self.make_patient_payload()
        self.register_patient(patient_payload)
        original_token = self.login_and_get_token(patient_payload["email"], patient_payload["password"])

        response = self.client.get(
            f"{self.api_prefix}/user/login",
            headers=self.auth_headers(original_token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert "access_token" in body
        assert isinstance(body["access_token"], str)
        assert body["access_token"] != original_token

    def test_refresh_token_with_admin_returns_new_token(self):
        admin_user = self.create_admin()
        original_token = self.login_and_get_token(admin_user.email, self.default_password)

        response = self.client.get(
            f"{self.api_prefix}/user/login?hours_validity=2.5",
            headers=self.auth_headers(original_token),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body is not None
        assert "access_token" in body
        assert isinstance(body["access_token"], str)
        assert body["access_token"] != original_token
        new_token = body["access_token"]
        assert isinstance(new_token, str)
        assert new_token != original_token

        # Verify the token has the default expiration of 672 hours (28 days)
        with self.app.app_context():
            decoded = decode_token(new_token)
            exp_timestamp = decoded["exp"]
            iat_timestamp = decoded["iat"]

            # Calculate the difference in hours
            exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            iat_time = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)
            duration_hours = (exp_time - iat_time).total_seconds() / 3600

            # Allow a small tolerance for timing differences (within 1 minute = 1/60 hour)
            tolerance_hours = 1 / 60
            assert abs(duration_hours - 672) < tolerance_hours, f"Expected ~672 hours, got {duration_hours}"
