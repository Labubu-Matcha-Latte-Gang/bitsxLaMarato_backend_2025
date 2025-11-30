class BaseQuestionException(Exception):
    """Base exception for question-related errors."""
    pass

class QuestionNotFoundException(BaseQuestionException):
    """Exception raised when a question is not found."""
    pass

class QuestionCreationException(BaseQuestionException):
    """Exception raised when question creation fails."""
    pass

class QuestionUpdateException(BaseQuestionException):
    """Exception raised when updating a question fails."""
    pass

class QuestionDeletionException(BaseQuestionException):
    """Exception raised when deleting a question fails."""
    pass
