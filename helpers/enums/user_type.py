from enum import Enum

class UserType(Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"