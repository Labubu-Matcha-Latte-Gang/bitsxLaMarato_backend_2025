from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response, jsonify
from werkzeug.exceptions import HTTPException

from db import db
from sqlalchemy.exc import IntegrityError
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.user_exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException,
    UserRoleConflictException,
    RelatedUserNotFoundException,
)
from models.admin import Admin
from models.patient import Patient
from models.user import User
from models.doctor import Doctor
from schemas import (
    PatientRegisterSchema,
    DoctorRegisterSchema,
    UserLoginSchema,
    UserLoginResponseSchema,
    PatientEmailPathSchema,
    UserResponseSchema,
    UserUpdateSchema,
    UserPartialUpdateSchema,
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
    Patient Registration Endpoint
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(PatientRegisterSchema, location='json')
    @blp.response(201, description="Patient successfully registered")
    @blp.response(400, description="Bad Request")
    @blp.response(422, description="Unprocessable Entity")
    @blp.response(500, description="Internal Server Error")
    def post(self, data: dict) -> Response:
        """Register a new patient"""
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
    Doctor Registration Endpoint
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(DoctorRegisterSchema, location='json')
    @blp.response(201, description="Doctor successfully registered")
    @blp.response(400, description="Bad Request")
    @blp.response(422, description="Unprocessable Entity")
    @blp.response(500, description="Internal Server Error")
    def post(self, data: dict) -> Response:
        """Register a new doctor"""
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
    User Login Endpoint
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(UserLoginSchema, location='json')
    @blp.response(200, schema=UserLoginResponseSchema, description="User successfully logged in")
    @blp.response(400, description="Bad Request")
    @blp.response(401, description="Unauthorized")
    @blp.response(422, description="Unprocessable Entity")
    @blp.response(500, description="Internal Server Error")
    def post(self, data: dict) -> Response:
        """Login a user"""
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
    User CRUD Endpoint
    """

    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.response(200, schema=UserResponseSchema, description="My user information retrieved successfully.")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(500, description="Internal Server Error")
    def get(self):
        """Get my user information."""
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
    @blp.response(200, schema=UserResponseSchema, description="User information updated successfully.")
    @blp.response(400, description="Bad Request")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(500, description="Internal Server Error")
    def put(self, data: dict):
        """Replace user information (name, surname, and optionally password)."""
        try:
            email: str = get_jwt_identity()
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
    @blp.response(200, schema=UserResponseSchema, description="User information partially updated successfully.")
    @blp.response(400, description="Bad Request")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(500, description="Internal Server Error")
    def patch(self, data: dict):
        """Partially update user information (name, surname, or password)."""
        try:
            email: str = get_jwt_identity()
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
    @blp.response(204, description="User deleted successfully.")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(404, description="User not found.")
    @blp.response(500, description="Internal Server Error")
    def delete(self):
        """Delete the authenticated user."""
        try:
            email: str = get_jwt_identity()
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
    Patient data access endpoint for admins and authorized doctors.
    """

    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.arguments(PatientEmailPathSchema, location="path")
    @blp.response(200, schema=UserResponseSchema, description="Patient information retrieved successfully.")
    @blp.response(400, description="Bad Request")
    @blp.response(401, description="Missing or invalid JWT.")
    @blp.response(403, description="Forbidden")
    @blp.response(404, description="Patient not found.")
    @blp.response(500, description="Internal Server Error")
    def get(self, path_args: dict):
        """Get patient information by email for admins or assigned doctors."""
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
