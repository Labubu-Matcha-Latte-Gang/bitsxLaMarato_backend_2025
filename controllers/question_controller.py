from __future__ import annotations
from abc import ABC, abstractmethod
import uuid

from models.question import Question
from helpers.exceptions.question_exceptions import (
    QuestionCreationException,
    QuestionNotFoundException,
    QuestionUpdateException,
)

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
    def list_questions(self, filters: dict) -> list[Question]:
        """
        Retrieve questions matching optional filters.
        Args:
            filters (dict): Dictionary with optional keys: id, difficulty, question_type.
        Returns:
            list[Question]: Questions that match the filters.
        Raises:
            QuestionNotFoundException: If an ID filter is provided but no question matches.
        """
        raise NotImplementedError("list_questions method must be implemented by subclasses.")
    
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
    def create_questions(self, questions_data: list[dict]) -> list[Question]:
        """
        Create multiple questions.
        Args:
            questions_data (list[dict]): List of question payloads.
        Returns:
            list[Question]: Created questions.
        """
        raise NotImplementedError("create_questions method must be implemented by subclasses.")
    
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
    
    @abstractmethod
    def delete_question(self, question_id: uuid.UUID) -> Question:
        """
        Delete a question by its ID.
        Args:
            question_id (uuid.UUID): The ID of the question to delete.
        Returns:
            Question: The deleted question.
        Raises:
            QuestionNotFoundException: If no question is found with the given ID.
        """
        raise NotImplementedError("delete_question method must be implemented by subclasses.")

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
    
    def list_questions(self, filters: dict) -> list[Question]:
        query = Question.query

        question_id = filters.get('id')
        difficulty = filters.get('difficulty')
        difficulty_min = filters.get('difficulty_min')
        difficulty_max = filters.get('difficulty_max')
        question_type = filters.get('question_type')

        if question_id:
            query = query.filter(Question.id == question_id)
        if difficulty is not None:
            query = query.filter(Question.difficulty == difficulty)
        if difficulty_min is not None:
            query = query.filter(Question.difficulty >= difficulty_min)
        if difficulty_max is not None:
            query = query.filter(Question.difficulty <= difficulty_max)
        if question_type:
            query = query.filter(Question.question_type == question_type)

        questions = query.all()
        if question_id and not questions:
            raise QuestionNotFoundException(f"No s'ha trobat cap pregunta amb l'ID {question_id}.")
        return questions
    
    def create_question(self, question_data: dict) -> Question:
        try:
            question_payload = {
                "id": uuid.uuid4(),
                **question_data
            }
            question = Question(**question_payload)
            return question
        except Exception as exc:
            raise QuestionCreationException(f"No s'ha pogut crear la pregunta: {str(exc)}") from exc
    
    def create_questions(self, questions_data: list[dict]) -> list[Question]:
        try:
            return [self.create_question(question_data) for question_data in questions_data]
        except Exception as exc:
            raise QuestionCreationException(f"No s'han pogut crear les preguntes: {str(exc)}") from exc
    
    def update_question(self, question_id: uuid.UUID, update_data: dict) -> Question:
        question = self.get_question(question_id)
        try:
            question.set_properties(update_data)
        except Exception as exc:
            raise QuestionUpdateException(f"No s'ha pogut actualitzar la pregunta: {str(exc)}") from exc
        return question

    def delete_question(self, question_id: uuid.UUID) -> Question:
        question = self.get_question(question_id)
        return question
