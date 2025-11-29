from marshmallow import Schema, fields, validate
from helpers.enums.gender import Gender

GENDER_VALUES = [gender.value for gender in Gender]
GENDER_DESCRIPTION = f"Patient gender. Accepted values: {', '.join(GENDER_VALUES)}."

password_complexity = validate.Regexp(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$",
    error="Password must contain at least one uppercase letter, one lowercase letter, one number, and be at least 8 characters long.",
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
    name = fields.String(required=True, validate=validate.Length(max=80), metadata={"description": "Updated name of the user."})
    surname = fields.String(required=True, validate=validate.Length(max=80), metadata={"description": "Updated surname of the user."})
    password = fields.String(
        required=False,
        load_only=True,
        validate=password_complexity,
        metadata={"description": "New password for the user."},
    )
    ailments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "Patient ailments."})
    gender = fields.Enum(
        Gender,
        required=False,
        by_value=True,
        validate=validate.OneOf(GENDER_VALUES),
        metadata={"description": GENDER_DESCRIPTION, "enum": GENDER_VALUES},
    )
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
    name = fields.String(required=False, validate=validate.Length(max=80), metadata={"description": "Updated name of the user."})
    surname = fields.String(required=False, validate=validate.Length(max=80), metadata={"description": "Updated surname of the user."})
    password = fields.String(
        required=False,
        load_only=True,
        validate=password_complexity,
        metadata={"description": "New password for the user."},
    )
    ailments = fields.String(required=False, allow_none=True, validate=lambda s: len(s) <= 2048, metadata={"description": "Patient ailments."})
    gender = fields.Enum(
        Gender,
        required=False,
        by_value=True,
        validate=validate.OneOf(GENDER_VALUES),
        metadata={"description": GENDER_DESCRIPTION, "enum": GENDER_VALUES},
    )
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
    name = fields.String(required=True, validate=validate.Length(max=80), metadata={"description": "The name of the user."})
    surname = fields.String(required=True, validate=validate.Length(max=80), metadata={"description": "The surname of the user."})
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
    gender = fields.Enum(
        Gender,
        required=True,
        by_value=True,
        validate=validate.OneOf(GENDER_VALUES),
        metadata={"description": f"The gender of the patient. Accepted values: {', '.join(GENDER_VALUES)}.", "enum": GENDER_VALUES},
    )
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

class UserForgotPasswordSchema(Schema):
    """
    Schema for user forgot password data.
    """
    email = fields.Email(required=True, metadata={"description": "The email address of the user requesting password reset."})

class UserForgotPasswordResponseSchema(Schema):
    """
    Schema for user forgot password response data.
    """
    message = fields.String(required=True, metadata={"description": "Response message indicating the result of the password reset request."})
    validity = fields.Float(required=True, metadata={"description": "Validity duration of the password reset code in minutes."})

class UserResetPasswordSchema(Schema):
    """
    Schema for user reset password data.
    """
    email = fields.Email(required=True, metadata={"description": "The email address of the user resetting their password."})
    reset_code = fields.String(required=True, metadata={"description": "The reset code provided to the user."})
    new_password = fields.String(
        required=True,
        load_only=True,
        validate=password_complexity,
        metadata={"description": "The new password for the user."},
    )

class UserResetPasswordResponseSchema(Schema):
    """
    Schema for user reset password response data.
    """
    message = fields.String(required=True, metadata={"description": "Response message indicating the result of the password reset operation."})

class TranscriptionChunkSchema(Schema):
    """
    Schema for uploading an audio chunk.
    Note: The file itself is handled via multipart/form-data, verified in the controller.
    """
    session_id = fields.String(required=True, metadata={"description": "Unique identifier for the recording session."})
    chunk_index = fields.Integer(required=True, metadata={"description": "Sequential index of the chunk."})

class TranscriptionCompleteSchema(Schema):
    """
    Schema for finalizing the transcription session.
    """
    session_id = fields.String(required=True, metadata={"description": "Unique identifier for the recording session to finalize."})

class TranscriptionResponseSchema(Schema):
    """
    Schema for the final transcription response.
    """
    status = fields.String(required=True, metadata={"description": "Status of the operation."})
    transcription = fields.String(required=True, metadata={"description": "The complete combined transcription text."})