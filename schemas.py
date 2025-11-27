from marshmallow import Schema, fields, validate
from helpers.enums.gender import Gender

password_complexity = validate.Regexp(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$",
    error="Password must contain at least one uppercase letter, one lowercase letter, and one number.",
)

class PatientEmailPathSchema(Schema):
    """
    Schema for retrieving patient data by email via the URL path.
    """
    email = fields.Email(required=True, metadata={"description": "Patient email to retrieve data for."})

class UserResponseSchema(Schema):
    """
    Schema for user data responses (includes role-specific info when present).
    """
    email = fields.Email(required=True, metadata={"description": "User email."})
    name = fields.String(required=True, metadata={"description": "User name."})
    surname = fields.String(required=True, metadata={"description": "User surname."})
    role = fields.Dict(
        required=False,
        metadata={
            "description": (
                "Role-specific data. For patients: ailments, gender, age, treatments, height_cm, weight_kg, "
                "doctors (emails). For doctors: patients (emails). For admins: empty object."
            )
        },
    )

class UserUpdateSchema(Schema):
    """
    Schema for full user updates (PUT).
    """
    name = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "Updated name of the user."})
    surname = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "Updated surname of the user."})
    password = fields.String(
        required=False,
        load_only=True,
        validate=password_complexity,
        metadata={"description": "New password for the user."},
    )
    ailments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "Patient ailments."})
    gender = fields.Enum(Gender, required=False, metadata={"description": "Patient gender."})
    age = fields.Integer(required=False, allow_none=False, metadata={"description": "Patient age."})
    treatments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "Patient treatments."})
    height_cm = fields.Float(required=False, allow_none=False, metadata={"description": "Patient height in centimeters."})
    weight_kg = fields.Float(required=False, allow_none=False, metadata={"description": "Patient weight in kilograms."})
    doctors = fields.List(fields.Email(), required=False, metadata={"description": "List of doctor emails for the patient."})
    patients = fields.List(fields.Email(), required=False, metadata={"description": "List of patient emails for the doctor."})

class UserPartialUpdateSchema(Schema):
    """
    Schema for partial user updates (PATCH).
    """
    name = fields.String(required=False, validate=lambda s: len(s) <= 80, metadata={"description": "Updated name of the user."})
    surname = fields.String(required=False, validate=lambda s: len(s) <= 80, metadata={"description": "Updated surname of the user."})
    password = fields.String(
        required=False,
        load_only=True,
        validate=password_complexity,
        metadata={"description": "New password for the user."},
    )
    ailments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "Patient ailments."})
    gender = fields.Enum(Gender, required=False, metadata={"description": "Patient gender."})
    age = fields.Integer(required=False, allow_none=False, metadata={"description": "Patient age."})
    treatments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "Patient treatments."})
    height_cm = fields.Float(required=False, allow_none=False, metadata={"description": "Patient height in centimeters."})
    weight_kg = fields.Float(required=False, allow_none=False, metadata={"description": "Patient weight in kilograms."})
    doctors = fields.List(fields.Email(), required=False, metadata={"description": "List of doctor emails for the patient."})
    patients = fields.List(fields.Email(), required=False, metadata={"description": "List of patient emails for the doctor."})

class UserRegisterSchema(Schema):
    """
    Schema for user registration data.
    """
    name = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "The name of the user."})
    surname = fields.String(required=True, validate=lambda s: len(s) <= 80, metadata={"description": "The surname of the user."})
    email = fields.Email(required=True, metadata={"description": "The email address of the user."})
    password = fields.String(
        required=True,
        load_only=True,
        validate=password_complexity,
        metadata={"description": "The password for the user."},
    )

class PatientRegisterSchema(UserRegisterSchema):
    """Schema for patient registration data."""
    ailments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "The ailments of the patient."})
    gender = fields.Enum(Gender, required=True, metadata={"description": "The gender of the patient."})
    age = fields.Integer(required=True, allow_none=False, metadata={"description": "The age of the patient."})
    treatments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "The treatments of the patient."})
    height_cm = fields.Float(required=True, allow_none=False, metadata={"description": "The height of the patient in centimeters."})
    weight_kg = fields.Float(required=True, allow_none=False, metadata={"description": "The weight of the patient in kilograms."})
    doctors = fields.List(fields.Email(), required=False, metadata={"description": "List of doctor emails associated with the patient."})

class DoctorRegisterSchema(UserRegisterSchema):
    """Schema for doctor registration data."""
    patients = fields.List(fields.Email(), required=False, metadata={"description": "List of patient emails associated with the doctor."})

class UserLoginSchema(Schema):
    """
    Schema for user login data.
    """
    email = fields.Email(required=True, metadata={"description": "The email address of the user."})
    password = fields.String(required=True, load_only=True, metadata={"description": "The password for the user."})

class UserLoginResponseSchema(Schema):
    """
    Schema for user login response data.
    """
    access_token = fields.String(required=True, metadata={"description": "Authentication token for the user."})
