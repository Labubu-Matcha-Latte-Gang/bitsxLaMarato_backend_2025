class UserAlreadyExistsException(Exception):
    """Exception raised when trying to create a user that already exists."""
    pass

class InvalidCredentialsException(Exception):
    """Exception raised when user credentials are invalid."""
    pass

class UserNotFoundException(Exception):
    """Exception raised when a user is not found."""
    pass

class UnauthorizedAccessException(Exception):
    """Exception raised when a user tries to access a resource they are not authorized for."""
    pass

class UserRoleConflictException(Exception):
    """Exception raised when a user has zero or multiple roles assigned."""
    pass

class RelatedUserNotFoundException(Exception):
    """Exception raised when related users (doctors/patients) are not found."""
    pass

class InvalidResetCodeException(Exception):
    """Exception raised when a provided reset code is invalid or expired."""
    pass

class InvalidTokenException(Exception):
    """Exception raised when a JWT access token is invalid."""
    pass

class ExpiredTokenException(Exception):
    """Exception raised when a JWT access token has expired."""
    pass
