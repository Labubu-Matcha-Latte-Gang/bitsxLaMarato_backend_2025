from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from controllers.doctor_controller import IDoctorController
    from controllers.patient_controller import IPatientController
    from controllers.user_controller import IUserController
    from controllers.question_controller import IQuestionController

class AbstractControllerFactory(ABC):
    __instance: 'AbstractControllerFactory' = None

    @classmethod
    def get_instance(cls, inst: 'AbstractControllerFactory' | None = None) -> 'AbstractControllerFactory':
        """
        Get the singleton instance of the controller factory.
        Args:
            inst (AbstractControllerFactory | None): Optional instance to set as the singleton.
        Returns:
            AbstractControllerFactory: The instance of the controller factory.
        """
        if cls.__instance is None:
            cls.__instance = inst or ControllerFactory()
        return cls.__instance
    
    @abstractmethod
    def get_user_controller(self) -> IUserController:
        """
        Get the user controller instance.
        Returns:
            IUserController: The user controller instance.
        """
        raise NotImplementedError("get_user_controller method must be implemented by subclasses.")
    
    @abstractmethod
    def get_patient_controller(self) -> IPatientController:
        """
        Get the patient controller instance.
        Returns:
            IPatientController: The patient controller instance.
        """
        raise NotImplementedError("get_patient_controller method must be implemented by subclasses.")
    
    @abstractmethod
    def get_doctor_controller(self) -> IDoctorController:
        """
        Get the doctor controller instance.
        Returns:
            IDoctorController: The doctor controller instance.
        """
        raise NotImplementedError("get_doctor_controller method must be implemented by subclasses.")
    
    @abstractmethod
    def get_question_controller(self) -> IQuestionController:
        """
        Get the question controller instance.
        Returns:
            IQuestionController: The question controller instance.
        """
        raise NotImplementedError("get_question_controller method must be implemented by subclasses.")

class ControllerFactory(AbstractControllerFactory):
    def get_user_controller(self) -> IUserController:
        from controllers.user_controller import IUserController, UserController
        return IUserController.get_instance(UserController())
    
    def get_patient_controller(self) -> IPatientController:
        from controllers.patient_controller import IPatientController, PatientController
        return IPatientController.get_instance(PatientController())
    
    def get_doctor_controller(self) -> IDoctorController:
        from controllers.doctor_controller import IDoctorController, DoctorController
        return IDoctorController.get_instance(DoctorController())

    def get_question_controller(self) -> IQuestionController:
        from controllers.question_controller import IQuestionController, QuestionController
        return IQuestionController.get_instance(QuestionController())