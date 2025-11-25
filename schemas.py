from marshmallow import Schema, fields


class UserRegisterSchema(Schema):
    """Schema for user registration data."""

    name = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "The name of the user."})
    surname = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "The surname of the user."})
    email = fields.Email(required=True, metadata={"description": "The email address of the user."})
    password = fields.String(required=True, load_only=True, metadata={"description": "The password for the user."})