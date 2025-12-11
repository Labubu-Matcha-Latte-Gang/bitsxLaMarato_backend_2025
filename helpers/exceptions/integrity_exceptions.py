from helpers.exceptions.base import ApplicationException


class DataIntegrityException(ApplicationException):
    """Exception raised when database integrity constraints are violated."""
