class BaseActivityException(Exception):
    """Base exception for activity-related errors."""
    pass

class ActivityNotFoundException(BaseActivityException):
    """Exception raised when an activity is not found."""
    pass

class ActivityCreationException(BaseActivityException):
    """Exception raised when activity creation fails."""
    pass

class ActivityUpdateException(BaseActivityException):
    """Exception raised when updating an activity fails."""
    pass

class ActivityDeletionException(BaseActivityException):
    """Exception raised when deleting an activity fails."""
    pass
