class UserAlreadyExistsException(Exception):
    """Exception raised when trying to create a user that already exists."""
    pass

class InvalidCredentialsException(Exception):
    """Exception raised when user credentials are invalid."""
    pass

class UserNotFoundException(Exception):
    """Exception raised when a user is not found."""
    pass