from enum import Enum

class UserRole(Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"