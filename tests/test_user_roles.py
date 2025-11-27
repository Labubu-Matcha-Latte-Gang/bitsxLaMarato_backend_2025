from helpers.enums.gender import Gender
from models.doctor import Doctor
from models.patient import Patient
from models.user import User
from tests.base_test import BaseTest


class TestUserRoles(BaseTest):
    def test_login_without_role_returns_409(self):
        email = self.unique_email("norole")
        user = User(
            email=email,
            password=User.hash_password(self.default_password),
            name="No",
            surname="Role",
        )
        self.db.add(user)
        self.db.commit()

        response = self.login(email, self.default_password)

        assert response.status_code == 409

    def test_get_me_with_multiple_roles_returns_409(self):
        email = self.unique_email("multi")
        user = User(
            email=email,
            password=User.hash_password(self.default_password),
            name="Multi",
            surname="Role",
        )
        patient = Patient(
            email=email,
            ailments=None,
            gender=Gender.MALE,
            age=25,
            treatments=None,
            height_cm=175.0,
            weight_kg=70.0,
            user=user,
        )
        doctor = Doctor(email=email, user=user)
        self.db.add_all([user, patient, doctor])
        self.db.commit()

        token = self.generate_token(email)
        response = self.client.get(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 409

    def test_get_me_with_no_role_returns_409(self):
        email = self.unique_email("norole2")
        user = User(
            email=email,
            password=User.hash_password(self.default_password),
            name="No",
            surname="Role",
        )
        self.db.add(user)
        self.db.commit()

        token = self.generate_token(email)
        response = self.client.get(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 409

    def test_login_with_multiple_roles_returns_409(self):
        email = self.unique_email("multi-login")
        user = User(
            email=email,
            password=User.hash_password(self.default_password),
            name="Multi",
            surname="Role",
        )
        patient = Patient(
            email=email,
            ailments=None,
            gender=Gender.FEMALE,
            age=28,
            treatments=None,
            height_cm=165.0,
            weight_kg=60.0,
            user=user,
        )
        doctor = Doctor(email=email, user=user)
        self.db.add_all([user, patient, doctor])
        self.db.commit()

        response = self.login(email, self.default_password)

        assert response.status_code == 409
