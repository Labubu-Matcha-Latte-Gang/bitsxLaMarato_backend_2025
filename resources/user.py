from functools import lru_cache
from pathlib import Path

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response, jsonify
from werkzeug.exceptions import HTTPException

from db import db
from sqlalchemy.exc import IntegrityError
from globals import APPLICATION_EMAIL, RESET_CODE_VALIDITY_MINUTES
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.mail_exceptions import SendEmailException
from helpers.exceptions.user_exceptions import (
    InvalidResetCodeException,
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException,
    UserRoleConflictException,
    RelatedUserNotFoundException,
)
from helpers.factories.forgot_password import AbstractForgotPasswordFactory
from helpers.forgot_password.forgot_password import ForgotPasswordFacade
from models.admin import Admin
from models.patient import Patient
from models.user import User
from models.doctor import Doctor
from schemas import (
    PatientRegisterSchema,
    DoctorRegisterSchema,
    UserForgotPasswordResponseSchema,
    UserLoginSchema,
    UserLoginResponseSchema,
    PatientEmailPathSchema,
    UserResetPasswordResponseSchema,
    UserResetPasswordSchema,
    UserResponseSchema,
    UserUpdateSchema,
    UserPartialUpdateSchema,
    UserForgotPasswordSchema
)

blp = Blueprint('user', __name__, description='User related operations')

def _fetch_doctors_by_email(emails: list[str]) -> set[Doctor]:
    doctors:set[Doctor] = set()
    for email in emails:
        doctor = Doctor.query.get(email)
        if doctor is None:
            raise RelatedUserNotFoundException(f"Doctor not found: {email}")
        doctors.add(doctor)
    return doctors

def _fetch_patients_by_email(emails: list[str]) -> set[Patient]:
    patients:set[Patient] = set()
    for email in emails:
        patient = Patient.query.get(email)
        if patient is None:
            raise RelatedUserNotFoundException(f"Patient not found: {email}")
        patients.add(patient)
    return patients

@blp.route('/patient')
class PatientRegister(MethodView):
    """
    Endpoints for registering patient accounts.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(PatientRegisterSchema, location='json')
    @blp.doc(
        security=[],
        summary="Register patient",
        description="Creates a base user plus patient profile and links any provided doctor emails.",
    )
    @blp.response(201, schema=UserResponseSchema, description="Patient user created with patient role data.")
    @blp.response(400, description="Missing required field or the email is already registered.")
    @blp.response(404, description="Referenced doctor email not found.")
    @blp.response(422, description="Payload failed validation.")
    @blp.response(500, description="Unexpected server error while creating the patient.")
    def post(self, data: dict) -> Response:
        """
        Register a new patient user.

        Expects JSON that matches `PatientRegisterSchema`, including patient metrics and optional ailments,
        treatments, and doctor associations. Creates the user, creates the patient profile, and assigns the
        listed doctors.

        Status codes:
        - 201: Patient created; returns the created user payload.
        - 400: Missing required fields or email already exists.
        - 404: At least one doctor email could not be found.
        - 422: Payload failed schema validation.
        - 500: Unexpected error during creation.
        """
        try:
            safe_metadata = {k: v for k, v in data.items() if k != 'password'}
            self.logger.info("Start registering a patient", module="PatientRegister", metadata=safe_metadata)

            potential_existing_user = User.query.get(data['email'])
            if potential_existing_user:
                raise UserAlreadyExistsException("A user with this email already exists.")

            user_payload = {
                "email": data['email'],
                "password": User.hash_password(data['password']),
                "name": data['name'],
                "surname": data['surname'],
            }
            user = User(**user_payload)

            doctor_emails:list[str] = data.get('doctors', []) or []
            doctors = _fetch_doctors_by_email(doctor_emails)
            patient = Patient(
                ailments=data.get('ailments'),
                gender=data['gender'],
                age=data['age'],
                treatments=data.get('treatments'),
                height_cm=data['height_cm'],
                weight_kg=data['weight_kg'],
                email=data['email'],
                user=user,
            )

            db.session.add(user)
            db.session.add(patient)
            db.session.flush()
            patient.add_doctors(doctors)
            db.session.commit()

            return jsonify(user.to_dict()), 201
        except KeyError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to missing field", module="PatientRegister", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except UserAlreadyExistsException as e:
            db.session.rollback()
            self.logger.error("Patient register failed: User already exists", module="PatientRegister", metadata={"email": data['email']}, error=e)
            abort(400, message=str(e))
        except RelatedUserNotFoundException as e:
            db.session.rollback()
            self.logger.error("Patient register failed: Related doctor not found", module="PatientRegister", metadata={"email": data.get('email')}, error=e)
            abort(404, message=str(e))
        except ValueError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to invalid data", module="PatientRegister", error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to database integrity error", module="PatientRegister", error=e)
            abort(400, message="A user with this email already exists.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Patient register failed", module="PatientRegister", error=e)
            abort(500, message=str(e))

@blp.route('/doctor')
class DoctorRegister(MethodView):
    """
    Endpoints for registering doctor accounts.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(DoctorRegisterSchema, location='json')
    @blp.doc(
        security=[],
        summary="Register doctor",
        description="Creates a base user plus doctor profile and links any provided patients.",
    )
    @blp.response(201, schema=UserResponseSchema, description="Doctor user created with doctor role data.")
    @blp.response(400, description="Missing required field or the email is already registered.")
    @blp.response(404, description="Referenced patient email not found.")
    @blp.response(422, description="Payload failed validation.")
    @blp.response(500, description="Unexpected server error while creating the doctor.")
    def post(self, data: dict) -> Response:
        """
        Register a new doctor user.

        Expects JSON that matches `DoctorRegisterSchema`, creates the user and doctor profile, and links the
        provided patients when present.

        Status codes:
        - 201: Doctor created; returns the created user payload.
        - 400: Missing required fields or email already exists.
        - 404: At least one patient email could not be found.
        - 422: Payload failed schema validation.
        - 500: Unexpected error during creation.
        """
        try:
            safe_metadata = {k: v for k, v in data.items() if k != 'password'}
            self.logger.info("Start registering a doctor", module="DoctorRegister", metadata=safe_metadata)

            potential_existing_user = User.query.get(data['email'])
            if potential_existing_user:
                raise UserAlreadyExistsException("A user with this email already exists.")

            user_payload = {
                "email": data['email'],
                "password": User.hash_password(data['password']),
                "name": data['name'],
                "surname": data['surname'],
            }
            user = User(**user_payload)

            patient_emails:list[str] = data.get('patients', []) or []
            patients = _fetch_patients_by_email(patient_emails)
            doctor = Doctor(
                email=data['email'],
                user=user,
            )

            db.session.add(user)
            db.session.add(doctor)
            db.session.flush()
            doctor.add_patients(patients)
            db.session.commit()

            return jsonify(user.to_dict()), 201
        except KeyError as e:
            db.session.rollback()
            self.logger.error("Doctor register failed due to missing field", module="DoctorRegister", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except UserAlreadyExistsException as e:
            db.session.rollback()
            self.logger.error("Doctor register failed: User already exists", module="DoctorRegister", metadata={"email": data['email']}, error=e)
            abort(400, message=str(e))
        except RelatedUserNotFoundException as e:
            db.session.rollback()
            self.logger.error("Doctor register failed: Related patient not found", module="DoctorRegister", metadata={"email": data.get('email')}, error=e)
            abort(404, message=str(e))
        except ValueError as e:
            db.session.rollback()
            self.logger.error("Doctor register failed due to invalid data", module="DoctorRegister", error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Doctor register failed due to database integrity error", module="DoctorRegister", error=e)
            abort(400, message="A user with this email already exists.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Doctor register failed", module="DoctorRegister", error=e)
            abort(500, message=str(e))

@blp.route('/login')
class UserLogin(MethodView):
    """
    Authenticate users and issue JWT access tokens.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(UserLoginSchema, location='json')
    @blp.doc(
        security=[],
        summary="Login user",
        description="Authenticates a user with email and password and issues a JWT access token.",
    )
    @blp.response(200, schema=UserLoginResponseSchema, description="JWT access token issued for valid credentials.")
    @blp.response(400, description="Missing required login fields.")
    @blp.response(401, description="Invalid credentials.")
    @blp.response(409, description="User role conflict detected during login.")
    @blp.response(422, description="Payload failed validation.")
    @blp.response(500, description="Unexpected server error during authentication.")
    def post(self, data: dict) -> Response:
        """
        Authenticate a user and issue a JWT.

        Expects JSON that matches `UserLoginSchema` with an email and password. On success, returns an
        access token that can be used for authenticated endpoints.

        Status codes:
        - 200: Valid credentials; returns the JWT access token.
        - 400: Missing required login fields.
        - 401: Invalid credentials.
        - 409: User role state is inconsistent.
        - 422: Payload failed schema validation.
        - 500: Unexpected error during authentication.
        """
        try:
            self.logger.info("User login attempt", module="UserLogin", metadata={"email": data['email']})
            user:User|None = User.query.get(data['email'])
            if user and user.check_password(data['password']):
                user.get_role_instance()
                access_token = user.generate_jwt()
                return {"access_token": access_token}, 200
            else:
                raise InvalidCredentialsException("Invalid email or password.")
        except UserRoleConflictException as e:
            self.logger.error("User login failed: Role conflict", module="UserLogin", metadata={"email": data.get('email')}, error=e)
            abort(409, message=str(e))
        except KeyError as e:
            self.logger.error("User login failed due to missing field", module="UserLogin", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except InvalidCredentialsException as e:
            self.logger.error("User login failed: Invalid credentials", module="UserLogin", metadata={"email": data['email']}, error=e)
            abort(401, message=str(e))
        except ValueError as e:
            self.logger.error("User login failed: Value Error", module="UserLogin", error=e)
            abort(422, message=str(e))
        except Exception as e:
            self.logger.error("User login failed", module="UserLogin", error=e)
            abort(500, message=str(e))

@blp.route('')
class UserCRUD(MethodView):
    """
    Authenticated CRUD operations for the current user.
    """

    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.doc(
        summary="Get current user",
        description="Returns the authenticated user's profile including role data.",
    )
    @blp.response(200, schema=UserResponseSchema, description="Current user profile returned.")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(409, description="User role conflict detected.")
    @blp.response(500, description="Unexpected server error while retrieving the user.")
    def get(self):
        """
        Retrieve the authenticated user's profile.

        Returns the base user data plus role-specific information for the current identity.

        Status codes:
        - 200: User found and returned.
        - 401: Missing or invalid authentication token.
        - 404: User does not exist.
        - 409: User role configuration is inconsistent.
        - 500: Unexpected error while fetching the user.
        """
        try:
            self.logger.info("Fetching user information", module="UserCRUD")
            email:str = get_jwt_identity()
            user:User|None = User.query.get(email)
            if not user:
                raise UserNotFoundException("User not found.")
            return jsonify(user.to_dict()), 200
        except UserRoleConflictException as e:
            self.logger.error("User role conflict", module="UserCRUD", error=e)
            abort(409, message=str(e))
        except UserNotFoundException as e:
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except Exception as e:
            self.logger.error("Fetching user information failed", module="UserCRUD", error=e)
            abort(500, message=str(e))

    @jwt_required()
    @blp.arguments(UserUpdateSchema, location='json')
    @blp.doc(
        summary="Replace current user",
        description="Fully replaces the authenticated user's profile and role data, resetting doctor/patient associations.",
    )
    @blp.response(200, schema=UserResponseSchema, description="User updated with the provided data.")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(409, description="User role conflict detected.")
    @blp.response(422, description="Payload failed validation.")
    @blp.response(500, description="Unexpected server error while updating the user.")
    def put(self, data: dict):
        """
        Fully replace the authenticated user's profile.

        Expects JSON that matches `UserUpdateSchema`. Updates personal data, password when provided, and
        replaces doctor/patient associations for the role with the provided values.

        Status codes:
        - 200: User updated and returned.
        - 401: Missing or invalid authentication token.
        - 404: User does not exist or related user not found.
        - 409: User role configuration is inconsistent.
        - 422: Payload failed schema validation.
        - 500: Unexpected error while updating the user.
        """
        email: str | None = None
        try:
            email = get_jwt_identity()
            user: User | None = User.query.get(email)
            if not user:
                raise UserNotFoundException("User not found.")

            update_fields = [field for field in data.keys() if field != "password"]
            self.logger.info(
                "Updating user information (PUT)",
                module="UserCRUD",
                metadata={"email": email, "fields_updated": update_fields}
            )

            user.set_properties(data)

            doctor_emails:list[str] = data.get('doctors', []) or []
            patient_emails:list[str] = data.get('patients', []) or []

            data['doctors'] = _fetch_doctors_by_email(doctor_emails)
            data['patients'] = _fetch_patients_by_email(patient_emails)

            role_instance = user.get_role_instance()
            role_instance.remove_all_associations()
            role_instance.set_properties(data)

            db.session.commit()
            return jsonify(user.to_dict()), 200
        except RelatedUserNotFoundException as e:
            db.session.rollback()
            self.logger.error("User update failed: Related user not found", module="UserCRUD", metadata={"email": email}, error=e)
            abort(404, message=str(e))
        except UserRoleConflictException as e:
            db.session.rollback()
            self.logger.error("User update failed due to role conflict", module="UserCRUD", metadata={"email": email}, error=e)
            abort(409, message=str(e))
        except UserNotFoundException as e:
            db.session.rollback()
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except HTTPException as e:
            db.session.rollback()
            raise e
        except Exception as e:
            db.session.rollback()
            self.logger.error("Updating user information failed", module="UserCRUD", error=e)
            abort(500, message=str(e))

    @jwt_required()
    @blp.arguments(UserPartialUpdateSchema, location='json')
    @blp.doc(
        summary="Partially update current user",
        description="Updates provided fields for the authenticated user and resets role associations when lists are supplied.",
    )
    @blp.response(200, schema=UserResponseSchema, description="User updated with the provided fields.")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(409, description="User role conflict detected.")
    @blp.response(422, description="Payload failed validation.")
    @blp.response(500, description="Unexpected server error while partially updating the user.")
    def patch(self, data: dict):
        """
        Partially update the authenticated user's profile.

        Accepts any subset of fields from `UserPartialUpdateSchema`. Updates personal data and password when
        provided. For patients/doctors, if association lists are provided, replaces them with the supplied
        values.

        Status codes:
        - 200: User updated and returned.
        - 401: Missing or invalid authentication token.
        - 404: User does not exist or related user not found.
        - 409: User role configuration is inconsistent.
        - 422: Payload failed schema validation.
        - 500: Unexpected error while updating the user.
        """
        email: str | None = None
        try:
            email = get_jwt_identity()
            user: User | None = User.query.get(email)
            if not user:
                raise UserNotFoundException("User not found.")

            update_fields = [field for field in data.keys() if field != "password"]
            self.logger.info(
                "Updating user information (PATCH)",
                module="UserCRUD",
                metadata={"email": email, "fields_updated": update_fields}
            )

            user.set_properties(data)

            role_instance = user.get_role_instance()
            role_data = dict(data)

            if isinstance(role_instance, Patient) and 'doctors' in data:
                doctor_emails:list[str] = data.get('doctors') or []
                new_doctors = _fetch_doctors_by_email(doctor_emails)
                role_instance.remove_all_associations()
                role_instance.add_doctors(new_doctors)
                role_data.pop('doctors', None)
            elif isinstance(role_instance, Doctor) and 'patients' in data:
                patient_emails:list[str] = data.get('patients') or []
                new_patients = _fetch_patients_by_email(patient_emails)
                role_instance.remove_all_associations()
                role_instance.add_patients(new_patients)
                role_data.pop('patients', None)

            role_instance.set_properties(role_data)

            db.session.commit()
            return jsonify(user.to_dict()), 200
        except RelatedUserNotFoundException as e:
            db.session.rollback()
            self.logger.error("Partial user update failed: Related user not found", module="UserCRUD", metadata={"email": email}, error=e)
            abort(404, message=str(e))
        except UserRoleConflictException as e:
            db.session.rollback()
            self.logger.error("Partial user update failed due to role conflict", module="UserCRUD", metadata={"email": email}, error=e)
            abort(409, message=str(e))
        except UserNotFoundException as e:
            db.session.rollback()
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except HTTPException as e:
            db.session.rollback()
            raise e
        except Exception as e:
            db.session.rollback()
            self.logger.error("Partially updating user information failed", module="UserCRUD", error=e)
            abort(500, message=str(e))

    @jwt_required()
    @blp.doc(
        summary="Delete current user",
        description="Deletes the authenticated user after removing all role associations.",
    )
    @blp.response(204, description="User deleted successfully.")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(409, description="User role conflict detected.")
    @blp.response(500, description="Unexpected server error while deleting the user.")
    def delete(self):
        """
        Delete the authenticated user's account.

        Removes any role associations, deletes the user record, and returns an empty 204 response.

        Status codes:
        - 204: User deleted.
        - 401: Missing or invalid authentication token.
        - 404: User does not exist.
        - 409: User role configuration is inconsistent.
        - 500: Unexpected error while deleting the user.
        """
        email: str | None = None
        try:
            email = get_jwt_identity()
            user: User | None = User.query.get(email)
            if not user:
                raise UserNotFoundException("User not found.")

            self.logger.info("Deleting user", module="UserCRUD", metadata={"email": email})

            role_instance = user.get_role_instance()
            role_instance.remove_all_associations()

            db.session.delete(user)
            db.session.commit()

            return Response(status=204)
        except UserRoleConflictException as e:
            db.session.rollback()
            self.logger.error("Deleting user failed due to role conflict", module="UserCRUD", metadata={"email": email}, error=e)
            abort(409, message=str(e))
        except UserNotFoundException as e:
            db.session.rollback()
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except Exception as e:
            db.session.rollback()
            self.logger.error("Deleting user failed", module="UserCRUD", error=e)
            abort(500, message=str(e))

@blp.route('/<string:email>')
class PatientData(MethodView):
    """
    Patient data access endpoint for admins, assigned doctors, and the patient themselves.
    """

    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.arguments(PatientEmailPathSchema, location="path")
    @blp.doc(
        summary="Get patient by email",
        description="Admins can fetch any patient; doctors only if assigned; patients can fetch their own record.",
    )
    @blp.response(200, schema=UserResponseSchema, description="Patient information retrieved successfully.")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(403, description="The authenticated user is not allowed to view this patient.")
    @blp.response(404, description="Patient not found.")
    @blp.response(409, description="User role conflict detected.")
    @blp.response(500, description="Unexpected server error while retrieving the patient.")
    def get(self, path_args: dict, **kwargs):
        """
        Retrieve patient information by email with role-based authorization.

        Requires a valid JWT. Admins can view any patient. Doctors can view patients they are assigned to.
        Patients can view their own record.

        Status codes:
        - 200: Patient information returned.
        - 401: Missing or invalid authentication token.
        - 403: Authenticated user lacks permission to view the patient.
        - 404: Patient does not exist.
        - 409: User role configuration is inconsistent.
        - 500: Unexpected error while fetching the patient.
        """
        patient_email = None
        try:
            patient_email = path_args.get('email')

            self.logger.info(
                "Fetching patient information",
                module="PatientData",
                metadata={"patient_email": patient_email}
            )

            patient: Patient | None = Patient.query.get(patient_email)
            if not patient:
                raise UserNotFoundException("Patient not found.")

            current_user_email: str = get_jwt_identity()
            current_user: User | None = User.query.get(current_user_email)
            if not current_user:
                abort(401, message="Invalid authentication token.")

            role_instance:Admin|Doctor|Patient = current_user.get_role_instance()

            authorized = False
            if current_user_email == patient_email:
                authorized = True
            elif isinstance(role_instance, Admin):
                authorized = True
            elif isinstance(role_instance, Doctor) and role_instance.doctor_of_this_patient(patient):
                authorized = True

            if not authorized:
                abort(403, message="You do not have permission to access this patient's data.")

            patient_payload = patient.get_user().to_dict()
            return jsonify(patient_payload), 200

        except UserRoleConflictException as e:
            self.logger.error("User role conflict", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(409, message=str(e))
        except UserNotFoundException as e:
            self.logger.error("Patient not found", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(404, message=str(e))
        except HTTPException as e:
            self.logger.error("HTTP exception occurred", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            raise e
        except Exception as e:
            self.logger.error("Fetching patient information failed", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(500, message=str(e))

@blp.route('/forgot-password')
class UserForgotPassword(MethodView):
    """
    Endpoints for requesting and completing password resets.
    """

    logger = AbstractLogger.get_instance()

    RESET_PASSWORD_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "mail_reset_password.html"

    @lru_cache(maxsize=1)
    def _load_reset_password_template(self) -> str:
        return self.RESET_PASSWORD_TEMPLATE_PATH.read_text(encoding='utf-8')

    @blp.arguments(UserForgotPasswordSchema, location='json')
    @blp.doc(
        security=[],
        summary="Request password reset",
        description="Sends a reset code email using the configured password reset template.",
    )
    @blp.response(200, schema=UserForgotPasswordResponseSchema, description="Reset email sent; includes validity minutes.")
    @blp.response(400, description="Missing required field.")
    @blp.response(401, description="Invalid credentials for the reset request.")
    @blp.response(404, description="User not found for the provided email.")
    @blp.response(409, description="User role conflict detected.")
    @blp.response(422, description="Payload failed validation.")
    @blp.response(500, description="Failed to load the email template or send the reset email.")
    def post(self, data: dict) -> Response:
        """
        Initiate the password reset flow.

        Expects JSON that matches `UserForgotPasswordSchema` with the user's email. Loads the reset email
        template, generates and sends a reset code, and returns the validity window for the code.

        Status codes:
        - 200: Reset email sent successfully.
        - 400: Required field missing.
        - 401: Invalid credentials provided.
        - 404: User does not exist.
        - 409: User role configuration is inconsistent.
        - 422: Payload failed schema validation.
        - 500: Failed to load the template or send the email.
        """
        try:
            self.logger.info("A user forgot their password", module="UserForgotPassword", metadata={"email": data['email']})

            try:
                template = self._load_reset_password_template()
            except OSError as e:
                self.logger.error("Failed to load reset password template", module="UserForgotPassword", error=e)
                abort(500, message="Failed to load reset email template.")

            factory = AbstractForgotPasswordFactory.get_instance()
            forgot_password_facade = factory.get_password_facade()
            forgot_password_facade.process_forgot_password(data['email'], APPLICATION_EMAIL, "Sol·licitud de canvi de contrasenya", template)

            response_payload = {"message": "El mail ha estat enviat exitosament a l'usuari.", "validity": RESET_CODE_VALIDITY_MINUTES}
            return jsonify(response_payload), 200
        
        except SendEmailException as e:
            self.logger.error("User forgot password failed: Email sending error", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(500, message="Failed to send reset email. Please try again later.")
        except UserRoleConflictException as e:
            self.logger.error("User forgot password failed: Role conflict", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(409, message=str(e))
        except UserNotFoundException as e:
            self.logger.error("User forgot password failed: User not found", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(404, message=str(e))
        except KeyError as e:
            self.logger.error("User forgot password failed due to missing field", module="UserForgotPassword", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except InvalidCredentialsException as e:
            self.logger.error("User forgot password failed: Invalid credentials", module="UserForgotPassword", metadata={"email": data['email']}, error=e)
            abort(401, message=str(e))
        except ValueError as e:
            self.logger.error("User forgot password failed: Value Error", module="UserForgotPassword", error=e)
            abort(422, message=str(e))
        except Exception as e:
            self.logger.error("User forgot password failed", module="UserForgotPassword", error=e)
            abort(500, message=str(e))

    @blp.arguments(UserResetPasswordSchema, location='json')
    @blp.doc(
        security=[],
        summary="Reset password with code",
        description="Validates the reset code and updates the user's password.",
    )
    @blp.response(200, schema=UserResetPasswordResponseSchema, description="Password reset successfully.")
    @blp.response(400, description="Missing field or reset code is invalid/expired.")
    @blp.response(401, description="Invalid credentials for the reset request.")
    @blp.response(404, description="User not found for the provided email.")
    @blp.response(409, description="User role conflict detected.")
    @blp.response(422, description="Payload failed validation.")
    @blp.response(500, description="Unexpected server error while resetting the password.")
    def patch(self, data: dict) -> Response:
        """
        Complete the password reset by validating the reset code and setting a new password.

        Expects JSON that matches `UserResetPasswordSchema` with the email, reset code, and new password.

        Status codes:
        - 200: Password reset successfully.
        - 400: Missing field or reset code invalid/expired.
        - 401: Invalid credentials provided.
        - 404: User does not exist.
        - 409: User role configuration is inconsistent.
        - 422: Payload failed schema validation.
        - 500: Unexpected error while resetting the password.
        """
        try:
            self.logger.info("A user wants to reset their password", module="UserForgotPassword", metadata={"email": data['email']})

            factory = AbstractForgotPasswordFactory.get_instance()
            forgot_password_facade = factory.get_password_facade()
            forgot_password_facade.reset_password(data['email'], data['reset_code'], data['new_password'])

            response_payload = {"message": "Contrasenya restablerta exitosament."}
            return jsonify(response_payload), 200
        
        except InvalidResetCodeException as e:
            self.logger.error("User reset password failed: Invalid or expired reset code", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(400, message=str(e))
        except UserRoleConflictException as e:
            self.logger.error("User reset password failed: Role conflict", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(409, message=str(e))
        except UserNotFoundException as e:
            self.logger.error("User reset password failed: User not found", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(404, message=str(e))
        except KeyError as e:
            self.logger.error("User reset password failed due to missing field", module="UserForgotPassword", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except InvalidCredentialsException as e:
            self.logger.error("User reset password failed: Invalid credentials", module="UserForgotPassword", metadata={"email": data['email']}, error=e)
            abort(401, message=str(e))
        except ValueError as e:
            self.logger.error("User reset password failed: Value Error", module="UserForgotPassword", error=e)
            abort(422, message=str(e))
        except Exception as e:
            self.logger.error("User reset password failed", module="UserForgotPassword", error=e)
            abort(500, message=str(e))
