from __future__ import annotations
from abc import ABC, abstractmethod
import uuid

from models.question import Question
from helpers.exceptions.question_exceptions import QuestionNotFoundException

class IQuestionController(ABC):
    __instance: 'IQuestionController' = None

    @abstractmethod
    def get_question(self, question_id: uuid.UUID) -> Question:
        """
        Retrieve a question by its ID.
        Args:
            question_id (uuid.UUID): The ID of the question to retrieve.
        Returns:
            Question: The question object corresponding to the provided ID.
        Raises:
            QuestionNotFoundException: If no question is found with the given ID.
        """
        raise NotImplementedError("get_question method must be implemented by subclasses.")
    
    @abstractmethod
    def create_question(self, question_data: dict) -> Question:
        """
        Create a new question with the provided data.
        Args:
            question_data (dict): A dictionary containing question attributes.
        Returns:
            Question: The newly created question object.
        Raises:
            QuestionCreationException: If there is an error during question creation.
        """
        raise NotImplementedError("create_question method must be implemented by subclasses.")
    
    @abstractmethod
    def update_question(self, question_id: uuid.UUID, update_data: dict) -> Question:
        """
        Update an existing question with the provided data.
        Args:
            question_id (uuid.UUID): The ID of the question to update.
            update_data (dict): A dictionary containing attributes to update.
        Returns:
            Question: The updated question object.
        Raises:
            QuestionNotFoundException: If no question is found with the given ID.
            QuestionUpdateException: If there is an error during question update.
        """
        raise NotImplementedError("update_question method must be implemented by subclasses.")

    @classmethod
    def get_instance(cls, inst: 'IQuestionController' | None = None) -> 'IQuestionController':
        """
        Get the singleton instance of the question controller.
        Args:
            inst (IQuestionController | None): Optional instance to set as the singleton.
        Returns:
            IQuestionController: The instance of the question controller.
        """
        if cls.__instance is None:
            cls.__instance = inst or QuestionController()
        return cls.__instance
    
class QuestionController(IQuestionController):
    def get_question(self, question_id: uuid.UUID) -> Question:
        question = Question.query.get(question_id)
        if not question:
            raise QuestionNotFoundException(f"No s'ha trobat cap pregunta amb l'ID {question_id}.")
        return question
    
    def create_question(self, question_data: dict) -> Question:
        question_payload = {
            "id": uuid.uuid4(),
            **question_data
        }
        question = Question(**question_payload)
        return question
    
    def update_question(self, question_id: uuid.UUID, update_data: dict) -> Question:
        question = self.get_question(question_id)
        question.set_properties(update_data)
        return question