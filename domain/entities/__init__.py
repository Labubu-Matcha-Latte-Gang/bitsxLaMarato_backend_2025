# Re-export domain entities for convenience.
from .user import User, Patient, Doctor, Admin
from .question import Question
from .activity import Activity

__all__ = ["User", "Patient", "Doctor", "Admin", "Question", "Activity"]
