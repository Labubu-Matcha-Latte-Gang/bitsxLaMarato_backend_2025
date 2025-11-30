class BaseQuestionException(Exception):
    """Base exception for question-related errors."""
    pass

class QuestionNotFoundException(BaseQuestionException):
    """Exception raised when a question is not found."""
    pass