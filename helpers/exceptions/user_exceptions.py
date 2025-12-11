from helpers.exceptions.base import ApplicationException


class UserAlreadyExistsException(ApplicationException):
    """Exception raised when trying to create a user that already exists."""


class InvalidCredentialsException(ApplicationException):
    """Exception raised when user credentials are invalid."""


class UserNotFoundException(ApplicationException):
    """Exception raised when a user is not found."""


class UnauthorizedAccessException(ApplicationException):
    """Exception raised when a user tries to access a resource they are not authorized for."""


class UserRoleConflictException(ApplicationException):
    """Exception raised when a user has zero or multiple roles assigned."""


class RelatedUserNotFoundException(ApplicationException):
    """Exception raised when related users (doctors/patients) are not found."""


class InvalidResetCodeException(ApplicationException):
    """Exception raised when a provided reset code is invalid or expired."""


class InvalidTokenException(ApplicationException):
    """Exception raised when a JWT access token is invalid."""


class ExpiredTokenException(ApplicationException):
    """Exception raised when a JWT access token has expired."""
