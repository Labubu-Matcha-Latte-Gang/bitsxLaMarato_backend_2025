from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response

from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.user_exceptions import UserAlreadyExistsException
from models.patient import Patient
from models.user import User
from models.doctor import Doctor
from schemas import PatientRegisterSchema

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