from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response, jsonify
from werkzeug.exceptions import HTTPException

from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.user_exceptions import UserAlreadyExistsException, InvalidCredentialsException, UserNotFoundException
from models.patient import Patient
from models.user import User
from models.doctor import Doctor
from schemas import PatientRegisterSchema, DoctorRegisterSchema, UserLoginSchema, UserLoginResponseSchema, PatientEmailPathSchema
from helpers.decorators import roles_required
from helpers.enums.user_role import UserRole

blp = Blueprint('user', __name__, description='User related operations')

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

            doctors = {Doctor.query.get(email) for email in data.get('doctors', [])}
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
            patient.add_doctors(doctors)

            db.session.add(user)
            db.session.add(patient)
            db.session.commit()

            return Response(status=201)
        except KeyError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to missing field", module="PatientRegister", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except UserAlreadyExistsException as e:
            db.session.rollback()
            self.logger.error("Patient register failed: User already exists", module="PatientRegister", metadata={"email": data['email']}, error=e)
            abort(400, message=str(e))
        except ValueError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to invalid data", module="PatientRegister", error=e)
            abort(422, message=str(e))
        except db.IntegrityError as e:
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

            patients = {Patient.query.get(email) for email in data.get('patients', [])}
            doctor = Doctor(
                email=data['email'],
                user=user,
            )
            doctor.add_patients(patients)

            db.session.add(user)
            db.session.add(doctor)
            db.session.commit()

            return Response(status=201)
        except KeyError as e:
            db.session.rollback()
            self.logger.error("Doctor register failed due to missing field", module="DoctorRegister", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except UserAlreadyExistsException as e:
            db.session.rollback()
            self.logger.error("Doctor register failed: User already exists", module="DoctorRegister", metadata={"email": data['email']}, error=e)
            abort(400, message=str(e))
        except ValueError as e:
            db.session.rollback()
            self.logger.error("Doctor register failed due to invalid data", module="DoctorRegister", error=e)
            abort(422, message=str(e))
        except db.IntegrityError as e:
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
                access_token = user.generate_jwt()
                return {"access_token": access_token}, 200
            else:
                raise InvalidCredentialsException("Invalid email or password.")
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
    @blp.response(200, description="My user information retrieved successfully.")
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
        except UserNotFoundException as e:
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except Exception as e:
            self.logger.error("Fetching user information failed", module="UserCRUD", error=e)
            abort(500, message=str(e))

@blp.route('/<string:email>')
class PatientData(MethodView):
    """
    Patient data access endpoint for admins and authorized doctors.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.ADMIN, UserRole.DOCTOR])
    @blp.arguments(PatientEmailPathSchema, location="path")
    @blp.response(200, description="Patient information retrieved successfully.")
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

            role_instance = current_user.get_role_instance()
            if isinstance(role_instance, Doctor) and patient not in role_instance.patients:
                abort(403, message="You do not have permission to access this patient's data.")

            return jsonify(patient.get_user().to_dict()), 200
        except UserNotFoundException as e:
            self.logger.error("Patient not found", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(404, message=str(e))
        except HTTPException as e:
            raise e
        except Exception as e:
            self.logger.error("Fetching patient information failed", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(500, message=str(e))
