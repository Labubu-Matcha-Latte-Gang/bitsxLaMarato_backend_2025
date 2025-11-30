from __future__ import annotations
from abc import ABC, abstractmethod

from helpers.exceptions.user_exceptions import RelatedUserNotFoundException, UserAlreadyExistsException, UserNotFoundException
from helpers.factories.controller_factories import AbstractControllerFactory
from models.doctor import Doctor
from models.user import User

class IDoctorController(ABC):
    __instance: 'IDoctorController' = None

    @abstractmethod
    def get_doctor(self, email: str) -> Doctor:
        """
        Retrieve a doctor by their email.
        Args:
            email (str): The email of the doctor to retrieve.
        Returns:
            Doctor: The doctor object corresponding to the provided email.
        Raises:
            UserNotFoundException: If no doctor is found with the given email.
        """
        raise NotImplementedError("get_doctor method must be implemented by subclasses.")
    
    @abstractmethod
    def create_doctor(self, doctor_data: dict) -> Doctor:
        """
        Create a new doctor with the provided data.
        Args:
            doctor_data (dict): A dictionary containing doctor attributes.
        Returns:
            Doctor: The newly created doctor object.
        Raises:
            UserCreationException: If there is an error during doctor creation.
        """
        raise NotImplementedError("create_doctor method must be implemented by subclasses.")
    
    @abstractmethod
    def update_doctor(self, user: User, update_data: dict) -> Doctor:
        """
        Update an existing doctor with the provided data.
        Args:
            user (User): The user object of the doctor to update.
            update_data (dict): A dictionary containing attributes to update.
        Returns:
            Doctor: The updated doctor object.
        Raises:
            UserNotFoundException: If no doctor is found with the given email.
            UserUpdateException: If there is an error during doctor update.
        """
        raise NotImplementedError("update_doctor method must be implemented by subclasses.")
    
    @abstractmethod
    def fetch_doctors_by_email(self, emails: list[str]) -> set[Doctor]:
        """
        Fetch multiple patients by their email addresses.
        Args:
            emails (list[str]): A list of doctor email addresses.
        Returns:
            set[Doctor]: A set of doctor objects corresponding to the provided emails.
        Raises:
            RelatedUserNotFoundException: If any doctor is not found for the given emails.
        """
        raise NotImplementedError("fetch_doctors_by_email method must be implemented by subclasses.")
    
    @classmethod
    def get_instance(cls, inst: 'IDoctorController' | None = None) -> 'IDoctorController':
        """
        Get the singleton instance of the doctor controller.
        Args:
            inst (IDoctorController | None): Optional instance to set as the singleton.
        Returns:
            IDoctorController: The instance of the doctor controller.
        """
        if cls.__instance is None:
            cls.__instance = inst or DoctorController()
        return cls.__instance
    
class DoctorController(IDoctorController):
    def get_doctor(self, email: str) -> Doctor:
        doctor: Doctor | None = Doctor.query.get(email)
        if not doctor:
            raise UserNotFoundException("Doctor no trobat.")
        return doctor

    def create_doctor(self, doctor_data: dict) -> Doctor:
        potential_existing_patient = Doctor.query.get(doctor_data.get('email'))
        if potential_existing_patient:
            raise UserAlreadyExistsException("Ja existeix un doctor amb aquest correu.")
        
        new_patient = Doctor(**doctor_data)
        return new_patient
    
    def fetch_doctors_by_email(self, emails: list[str]) -> set[Doctor]:
        patients:set[Doctor] = set()
        for email in emails:
            doctor = Doctor.query.get(email)
            if doctor is None:
                raise RelatedUserNotFoundException(f"No s'ha trobat cap doctor amb el correu: {email}")
            patients.add(doctor)
        return patients

    def update_doctor(self, user: User, update_data: dict) -> Doctor:
        doctor: Doctor | None = user.get_role_instance()
        if not doctor:
            raise UserNotFoundException("Usuari no trobat.")
        
        patient_emails:list[str] = update_data.get('patients', []) or []

        factory = AbstractControllerFactory.get_instance()
        patient_controller = factory.get_patient_controller()
        update_data['patients'] = patient_controller.fetch_patients_by_email(patient_emails)

        role_instance = user.get_role_instance()
        role_instance.remove_all_associations_between_user_roles()
        role_instance.set_properties(update_data)
