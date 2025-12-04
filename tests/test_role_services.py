from application.container import ServiceFactory
from domain.services.security import PasswordHasher
from helpers.enums.gender import Gender
from tests.base_test import BaseTest


class TestRoleServices(BaseTest):
    def test_patient_service_registers_and_links_doctor(self):
        factory = ServiceFactory.get_instance(session=self.db, refresh=True)
        doctor_service = factory.build_doctor_service()
        doctor_payload = self.make_doctor_payload()
        doctor = doctor_service.register_doctor(doctor_payload)

        patient_service = factory.build_patient_service()
        patient_payload = self.make_patient_payload(gender=Gender.MALE, doctors=[doctor.email])
        patient = patient_service.register_patient(patient_payload)

        assert doctor.email in patient.doctor_emails

        refreshed_doctor = doctor_service.get_doctor(doctor.email)
        assert patient.email in refreshed_doctor.patient_emails

    def test_doctor_service_registers_and_links_patients(self):
        factory = ServiceFactory.get_instance(session=self.db, refresh=True)
        patient_service = factory.build_patient_service()
        patient_payload = self.make_patient_payload(gender=Gender.FEMALE)
        patient = patient_service.register_patient(patient_payload)

        doctor_service = factory.build_doctor_service()
        doctor_payload = self.make_doctor_payload(patients=[patient.email])
        doctor = doctor_service.register_doctor(doctor_payload)

        assert patient.email in doctor.patient_emails

        refreshed_patient = patient_service.get_patient(patient.email)
        assert doctor.email in refreshed_patient.doctor_emails

    def test_admin_service_register_and_update_password(self):
        factory = ServiceFactory.get_instance(session=self.db, refresh=True)
        admin_service = factory.build_admin_service()

        admin_email = self.unique_email("admin")
        admin = admin_service.register_admin(
            admin_email,
            self.default_password,
            "Admin",
            "User",
        )

        new_password = "NewPassword1"
        updated_admin = admin_service.update_admin(admin.email, {"password": new_password})

        hasher = PasswordHasher()
        assert hasher.verify(new_password, updated_admin.password_hash)
