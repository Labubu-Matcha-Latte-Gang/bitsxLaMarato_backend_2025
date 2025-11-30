from __future__ import annotations
from abc import ABC, abstractmethod

from helpers.exceptions.user_exceptions import RelatedUserNotFoundException, UserAlreadyExistsException, UserNotFoundException
from helpers.factories.controller_factories import AbstractControllerFactory
from models.patient import Patient
from models.user import User

class IPatientController(ABC):
    __instance: 'IPatientController' = None

    @abstractmethod
    def get_patient(self, email: str) -> Patient:
        """
        Retrieve a patient by their email.
        Args:
            email (str): The email of the patient to retrieve.
        Returns:
            Patient: The patient object corresponding to the provided email.
        Raises:
            UserNotFoundException: If no patient is found with the given email.
        """
        raise NotImplementedError("get_patient method must be implemented by subclasses.")
    
    @abstractmethod
    def create_patient(self, patient_data: dict) -> Patient:
        """
        Create a new patient with the provided data.
        Args:
            patient_data (dict): A dictionary containing patient attributes.
        Returns:
            Patient: The newly created patient object.
        Raises:
            UserCreationException: If there is an error during patient creation.
        """
        raise NotImplementedError("create_patient method must be implemented by subclasses.")
    
    @abstractmethod
    def update_patient(self, user: User, update_data: dict) -> Patient:
        """
        Update an existing patient with the provided data.
        Args:
            user (User): The user object of the patient to update.
            update_data (dict): A dictionary containing attributes to update.
        Returns:
            Patient: The updated patient object.
        Raises:
            UserNotFoundException: If no patient is found with the given email.
            UserUpdateException: If there is an error during patient update.
        """
        raise NotImplementedError("update_patient method must be implemented by subclasses.")
    
    @abstractmethod
    def fetch_patients_by_email(self, emails: list[str]) -> set[Patient]:
        """
        Fetch multiple patients by their email addresses.
        Args:
            emails (list[str]): A list of patient email addresses.
        Returns:
            set[Patient]: A set of patient objects corresponding to the provided emails.
        Raises:
            RelatedUserNotFoundException: If any patient is not found for the given emails.
        """
        raise NotImplementedError("fetch_patients_by_email method must be implemented by subclasses.")
    
    @classmethod
    def get_instance(cls, inst: 'IPatientController' | None = None) -> 'IPatientController':
        """
        Get the singleton instance of the patient controller.
        Args:
            inst (IPatientController | None): Optional instance to set as the singleton.
        Returns:
            IPatientController: The instance of the patient controller.
        """
        if cls.__instance is None:
            cls.__instance = inst or PatientController()
        return cls.__instance
    
class PatientController(IPatientController):
    def get_patient(self, email: str) -> Patient:
        patient: Patient | None = Patient.query.get(email)
        if not patient:
            raise UserNotFoundException("Pacient no trobat.")
        return patient

    def create_patient(self, patient_data: dict) -> Patient:
        potential_existing_patient = Patient.query.get(patient_data.get('email'))
        if potential_existing_patient:
            raise UserAlreadyExistsException("Ja existeix un pacient amb aquest correu.")
        
        new_patient = Patient(**patient_data)
        return new_patient
    
    def fetch_patients_by_email(self, emails: list[str]) -> set[Patient]:
        patients:set[Patient] = set()
        for email in emails:
            patient = Patient.query.get(email)
            if patient is None:
                raise RelatedUserNotFoundException(f"No s'ha trobat cap pacient amb el correu: {email}")
            patients.add(patient)
        return patients

    def update_patient(self, user: User, update_data: dict) -> Patient:
        patient: Patient | None = user.get_role_instance()
        if not patient:
            raise UserNotFoundException("Usuari no trobat.")
        
        doctor_emails:list[str] = update_data.get('doctors', []) or []

        factory = AbstractControllerFactory.get_instance()
        doctor_controller = factory.get_doctor_controller()
        update_data['doctors'] = doctor_controller.fetch_doctors_by_email(doctor_emails)

        role_instance = user.get_role_instance()
        role_instance.remove_all_associations_between_user_roles()
        role_instance.set_properties(update_data)
