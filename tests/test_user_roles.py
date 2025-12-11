from helpers.enums.gender import Gender
from helpers.enums.user_role import UserRole
from models.doctor import Doctor
from models.patient import Patient
from models.user import User
from tests.base_test import BaseTest


class TestUserRoles(BaseTest):
    def test_login_without_role_returns_409(self):
        email = self.unique_email("norole")
        self.db.execute(
            User.__table__.insert().values(
                email=email,
                password=User.hash_password(self.default_password),
                name="No",
                surname="Role",
                role=UserRole.PATIENT,
            )
        )
        self.db.commit()

        response = self.login(email, self.default_password)

        assert response.status_code == 409

    def test_get_me_with_multiple_roles_returns_409(self):
        email = self.unique_email("multi")
        self.db.execute(
            User.__table__.insert().values(
                email=email,
                password=User.hash_password(self.default_password),
                name="Multi",
                surname="Role",
                role=UserRole.DOCTOR,
            )
        )
        self.db.execute(
            Patient.__table__.insert().values(
                email=email,
                ailments=None,
                gender=Gender.MALE,
                age=25,
                treatments=None,
                height_cm=175.0,
                weight_kg=70.0,
            )
        )
        self.db.execute(
            Doctor.__table__.insert().values(
                email=email,
                gender=Gender.MALE,
            )
        )
        self.db.commit()

        token = self.generate_token(email)
        response = self.client.get(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 409

    def test_get_me_with_no_role_returns_409(self):
        email = self.unique_email("norole2")
        self.db.execute(
            User.__table__.insert().values(
                email=email,
                password=User.hash_password(self.default_password),
                name="No",
                surname="Role",
                role=UserRole.PATIENT,
            )
        )
        self.db.commit()

        token = self.generate_token(email)
        response = self.client.get(
            f"{self.api_prefix}/user",
            headers=self.auth_headers(token),
        )

        assert response.status_code == 409

    def test_login_with_multiple_roles_returns_409(self):
        email = self.unique_email("multi-login")
        hashed = User.hash_password(self.default_password)
        self.db.execute(
            User.__table__.insert().values(
                email=email,
                password=hashed,
                name="Multi",
                surname="Role",
                role=UserRole.DOCTOR,
            )
        )
        self.db.execute(
            Patient.__table__.insert().values(
                email=email,
                ailments=None,
                gender=Gender.FEMALE,
                age=28,
                treatments=None,
                height_cm=165.0,
                weight_kg=60.0,
            )
        )
        self.db.execute(
            Doctor.__table__.insert().values(
                email=email,
                gender=Gender.MALE,
            )
        )
        self.db.commit()

        response = self.login(email, self.default_password)

        assert response.status_code == 409
