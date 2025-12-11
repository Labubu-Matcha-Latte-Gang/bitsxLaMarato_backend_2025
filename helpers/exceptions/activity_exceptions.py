from helpers.exceptions.base import ApplicationException


class BaseActivityException(ApplicationException):
    """Base exception for activity-related errors."""


class ActivityNotFoundException(BaseActivityException):
    """Exception raised when an activity is not found."""


class ActivityCreationException(BaseActivityException):
    """Exception raised when activity creation fails."""


class ActivityUpdateException(BaseActivityException):
    """Exception raised when updating an activity fails."""


class ActivityDeletionException(BaseActivityException):
    """Exception raised when deleting an activity fails."""
