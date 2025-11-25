from marshmallow import Schema, fields
from helpers.enums.user_type import UserType

class UserRegisterSchema(Schema):
    """Schema for user registration data."""

    name = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "The name of the user."})
    surname = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "The surname of the user."})
    email = fields.Email(required=True, metadata={"description": "The email address of the user."})
    password = fields.String(required=True, load_only=True, metadata={"description": "The password for the user."})
    role = fields.Enum(UserType, required=False, load_default=UserType.PATIENT, dump_default=UserType.PATIENT, metadata={"description": "The role of the user."})
    ailments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 1024, metadata={"description": "The ailments of the patient, if applicable."})