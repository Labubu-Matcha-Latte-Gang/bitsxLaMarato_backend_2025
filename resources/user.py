from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response

from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.user_exceptions import UserAlreadyExistsException
from models.patient import Patient
from models.user import User
from schemas import UserRegisterSchema, PatientRegisterSchema

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
            self.logger.info("Start registering a patient", module="PatientRegister", metadata=data)

            potential_existing_user = User.query.get(data['email'])
            if potential_existing_user:
                self.logger.warning("Patient register failed: User already exists", module="PatientRegister", metadata={"email": data['email']})
                raise UserAlreadyExistsException("A user with this email already exists.")

            user_payload = {
                "email": data['email'],
                "password": User.hash_password(data['password']),
                "name": data['name'],
                "surname": data['surname'],
            }
            user = User(**user_payload)
            db.session.add(user)

            patient_payload = {
                "email": data['email'],
                "ailments": data.get('ailments'),
                "gender": data['gender'],
                "age": data['age'],
                "treatments": data.get('treatments'),
                "height_cm": data['height_cm'],
                "weight_kg": data['weight_kg'],
            }
            patient = Patient(**patient_payload)
            db.session.add(patient)
            db.session.commit()
        except KeyError as e:
            self.logger.error("Patient register failed due to missing field", module="PatientRegister", error=e)
            abort(400, message=f"Missing field: {str(e)}")
        except UserAlreadyExistsException as e:
            abort(400, message=str(e))
        except ValueError as e:
            self.logger.error("Patient register failed due to invalid data", module="PatientRegister", error=e)
            abort(422, message=str(e))
        except db.IntegrityError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to database integrity error", module="PatientRegister", error=e)
            abort(400, message="A user with this email already exists.")
        except Exception as e:
            self.logger.error("Patient register failed", module="PatientRegister", error=e)
            abort(500, message=str(e))