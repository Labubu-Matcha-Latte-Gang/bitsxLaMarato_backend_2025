from helpers.exceptions.base import ApplicationException


class BaseQuestionException(ApplicationException):
    """Base exception for question-related errors."""


class QuestionNotFoundException(BaseQuestionException):
    """Exception raised when a question is not found."""


class QuestionCreationException(BaseQuestionException):
    """Exception raised when question creation fails."""


class QuestionUpdateException(BaseQuestionException):
    """Exception raised when updating a question fails."""


class QuestionDeletionException(BaseQuestionException):
    """Exception raised when deleting a question fails."""


class QuestionAnswerPersistenceException(BaseQuestionException):
    """Exception raised when storing an answered question fails."""
