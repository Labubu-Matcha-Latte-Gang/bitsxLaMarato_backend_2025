from functools import lru_cache
from pathlib import Path

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response, jsonify, g
from werkzeug.exceptions import HTTPException

from db import db
from sqlalchemy.exc import IntegrityError
from globals import APPLICATION_EMAIL, RESET_CODE_VALIDITY_MINUTES
from helpers.debugger.logger import AbstractLogger
from helpers.decorators import roles_required
from helpers.exceptions.mail_exceptions import SMTPCredentialsException, SendEmailException
from helpers.exceptions.user_exceptions import (
    InvalidResetCodeException,
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException,
    UserRoleConflictException,
    RelatedUserNotFoundException,
)
from helpers.enums.user_role import UserRole
from application.container import ServiceFactory
from helpers.forgot_password.forgot_password import AbstractForgotPasswordFacade
from helpers.email_service.adapter import AbstractEmailAdapter
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

blp = Blueprint('user', __name__, description="Operacions relacionades amb els usuaris")

@blp.route('/patient')
class PatientRegister(MethodView):
    """
    Endpoints for registering patient accounts.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(PatientRegisterSchema, location='json')
    @blp.doc(
        security=[],
        summary="Registrar pacient",
        description="Crea un usuari base amb perfil de pacient i enllaça els correus de metges indicats.",
    )
    @blp.response(201, schema=UserResponseSchema, description="Usuari pacient creat amb les dades de rol de pacient.")
    @blp.response(400, description="Falta un camp obligatori o el correu ja està registrat.")
    @blp.response(404, description="No s'ha trobat cap correu de metge indicat.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en crear el pacient.")
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

            user_service = ServiceFactory().build_user_service()
            patient = user_service.register_patient(data)

            return jsonify(patient.to_dict()), 201
        except KeyError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to missing field", module="PatientRegister", error=e)
            abort(400, message=f"Falta el camp: {str(e)}")
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
            abort(422, message=f"Dades no vàlides: {str(e)}")
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Patient register failed due to database integrity error", module="PatientRegister", error=e)
            abort(400, message="Ja existeix un usuari amb aquest correu.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Patient register failed", module="PatientRegister", error=e)
            abort(500, message=f"S'ha produït un error inesperat en registrar el pacient: {str(e)}")

@blp.route('/doctor')
class DoctorRegister(MethodView):
    """
    Endpoints for registering doctor accounts.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(DoctorRegisterSchema, location='json')
    @blp.doc(
        security=[],
        summary="Registrar metge",
        description="Crea un usuari base amb perfil de metge i enllaça els pacients indicats.",
    )
    @blp.response(201, schema=UserResponseSchema, description="Usuari metge creat amb les dades de rol de metge.")
    @blp.response(400, description="Falta un camp obligatori o el correu ja està registrat.")
    @blp.response(404, description="No s'ha trobat cap correu de pacient indicat.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en crear el metge.")
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

            factory = AbstractControllerFactory.get_instance()
            user_controller = factory.get_user_controller()

            user_payload = {
                "email": data['email'],
                "password": data['password'],
                "name": data['name'],
                "surname": data['surname'],
            }
            user = user_controller.create_user(user_payload)

            patient_controller = factory.get_patient_controller()

            patient_emails:list[str] = data.get('patients', []) or []
            patients = patient_controller.fetch_patients_by_email(patient_emails)

            doctor_controller = factory.get_doctor_controller()

            doctor_payload = {
                "email": data['email'],
                "user": user
            }
            doctor = doctor_controller.create_doctor(doctor_payload)

            db.session.add(user)
            db.session.add(doctor)
            db.session.flush()
            doctor.add_patients(patients)
            db.session.commit()

            return jsonify(user.to_dict()), 201
        except KeyError as e:
            db.session.rollback()
            self.logger.error("Doctor register failed due to missing field", module="DoctorRegister", error=e)
            abort(400, message=f"Falta el camp: {str(e)}")
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
            abort(422, message=f"Dades no vàlides: {str(e)}")
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Doctor register failed due to database integrity error", module="DoctorRegister", error=e)
            abort(400, message="Ja existeix un usuari amb aquest correu.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Doctor register failed", module="DoctorRegister", error=e)
            abort(500, message=f"S'ha produït un error inesperat en registrar el metge: {str(e)}")

@blp.route('/login')
class UserLogin(MethodView):
    """
    Authenticate users and issue JWT access tokens.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(UserLoginSchema, location='json')
    @blp.doc(
        security=[],
        summary="Iniciar sessió",
        description="Autentica un usuari amb correu i contrasenya i emet un token JWT.",
    )
    @blp.response(200, schema=UserLoginResponseSchema, description="Token JWT emès amb credencials vàlides.")
    @blp.response(400, description="Falten camps obligatoris d'inici de sessió.")
    @blp.response(401, description="Credencials no vàlides.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari durant l'inici de sessió.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor durant l'autenticació.")
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

            factory = AbstractControllerFactory.get_instance()
            user_controller = factory.get_user_controller()

            user = user_controller.get_user(data['email'])
            if user.check_password(data['password']):
                user.get_role_instance()
                access_token = user.generate_jwt()
                return {"access_token": access_token}, 200
            else:
                raise InvalidCredentialsException("Correu o contrasenya no vàlids.")
        except UserNotFoundException as e:
            self.logger.error("User login failed: User not found", module="UserLogin", metadata={"email": data['email']}, error=e)
            abort(401, message="Correu o contrasenya no vàlids.")
        except UserRoleConflictException as e:
            self.logger.error("User login failed: Role conflict", module="UserLogin", metadata={"email": data.get('email')}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except KeyError as e:
            self.logger.error("User login failed due to missing field", module="UserLogin", error=e)
            abort(400, message=f"Falta el camp: {str(e)}")
        except InvalidCredentialsException as e:
            self.logger.error("User login failed: Invalid credentials", module="UserLogin", metadata={"email": data['email']}, error=e)
            abort(401, message=str(e))
        except ValueError as e:
            self.logger.error("User login failed: Value Error", module="UserLogin", error=e)
            abort(422, message=f"Dades no vàlides: {str(e)}")
        except Exception as e:
            self.logger.error("User login failed", module="UserLogin", error=e)
            abort(500, message=f"S'ha produït un error inesperat en iniciar sessió: {str(e)}")

@blp.route('')
class UserCRUD(MethodView):
    """
    Authenticated CRUD operations for the current user.
    """

    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.doc(
        summary="Obtenir l'usuari actual",
        description="Retorna el perfil de l'usuari autenticat, incloses les dades del rol.",
    )
    @blp.response(200, schema=UserResponseSchema, description="Perfil de l'usuari actual retornat.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(404, description="Usuari no trobat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(500, description="Error inesperat del servidor en obtenir l'usuari.")
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

            factory = AbstractControllerFactory.get_instance()
            user_controller = factory.get_user_controller()

            user = user_controller.get_user(email)

            return jsonify(user.to_dict()), 200
        except UserRoleConflictException as e:
            self.logger.error("User role conflict", module="UserCRUD", error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except UserNotFoundException as e:
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except Exception as e:
            self.logger.error("Fetching user information failed", module="UserCRUD", error=e)
            abort(500, message=f"S'ha produït un error inesperat en obtenir l'usuari: {str(e)}")

    @jwt_required()
    @blp.arguments(UserUpdateSchema, location='json')
    @blp.doc(
        summary="Reemplaçar l'usuari actual",
        description="Substitueix completament el perfil de l'usuari autenticat i les dades del rol, reiniciant les associacions de metge/pacient.",
    )
    @blp.response(200, schema=UserResponseSchema, description="Usuari actualitzat amb les dades proporcionades.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(404, description="Usuari no trobat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en actualitzar l'usuari.")
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

            factory = AbstractControllerFactory.get_instance()
            user_controller = factory.get_user_controller()

            user = user_controller.update_user(email, data)

            update_fields = [field for field in data.keys() if field != "password"]
            self.logger.info(
                "Updating user information (PUT)",
                module="UserCRUD",
                metadata={"email": email, "fields_updated": update_fields}
            )

            db.session.commit()
            return jsonify(user.to_dict()), 200
        except RelatedUserNotFoundException as e:
            db.session.rollback()
            self.logger.error("User update failed: Related user not found", module="UserCRUD", metadata={"email": email}, error=e)
            abort(404, message=str(e))
        except UserRoleConflictException as e:
            db.session.rollback()
            self.logger.error("User update failed due to role conflict", module="UserCRUD", metadata={"email": email}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
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
            abort(500, message=f"S'ha produït un error inesperat en actualitzar l'usuari: {str(e)}")

    @jwt_required()
    @blp.arguments(UserPartialUpdateSchema, location='json')
    @blp.doc(
        summary="Actualitzar parcialment l'usuari actual",
        description="Actualitza els camps proporcionats per a l'usuari autenticat i reinicia les associacions de rol quan s'envien llistes.",
    )
    @blp.response(200, schema=UserResponseSchema, description="Usuari actualitzat amb els camps proporcionats.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(404, description="Usuari no trobat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en actualitzar parcialment l'usuari.")
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
            
            factory = AbstractControllerFactory.get_instance()
            user_controller = factory.get_user_controller()

            user = user_controller.update_user(email, data)

            update_fields = [field for field in data.keys() if field != "password"]
            self.logger.info(
                "Updating user information (PATCH)",
                module="UserCRUD",
                metadata={"email": email, "fields_updated": update_fields}
            )

            db.session.commit()
            return jsonify(user.to_dict()), 200
        except RelatedUserNotFoundException as e:
            db.session.rollback()
            self.logger.error("Partial user update failed: Related user not found", module="UserCRUD", metadata={"email": email}, error=e)
            abort(404, message=str(e))
        except UserRoleConflictException as e:
            db.session.rollback()
            self.logger.error("Partial user update failed due to role conflict", module="UserCRUD", metadata={"email": email}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
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
            abort(500, message=f"S'ha produït un error inesperat en actualitzar parcialment l'usuari: {str(e)}")

    @jwt_required()
    @blp.doc(
        summary="Eliminar l'usuari actual",
        description="Elimina l'usuari autenticat després d'esborrar totes les associacions de rol.",
    )
    @blp.response(204, description="Usuari eliminat correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(404, description="Usuari no trobat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(500, description="Error inesperat del servidor en eliminar l'usuari.")
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

            factory = AbstractControllerFactory.get_instance()
            user_controller = factory.get_user_controller()

            user = user_controller.get_user(email)

            self.logger.info("Deleting user", module="UserCRUD", metadata={"email": email})

            role_instance = user.get_role_instance()
            role_instance.remove_all_associations_between_user_roles()

            db.session.delete(user)
            db.session.commit()

            return Response(status=204)
        except UserRoleConflictException as e:
            db.session.rollback()
            self.logger.error("Deleting user failed due to role conflict", module="UserCRUD", metadata={"email": email}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except UserNotFoundException as e:
            db.session.rollback()
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except Exception as e:
            db.session.rollback()
            self.logger.error("Deleting user failed", module="UserCRUD", error=e)
            abort(500, message=f"S'ha produït un error inesperat en eliminar l'usuari: {str(e)}")

@blp.route('/<string:email>')
class PatientData(MethodView):
    """
    Patient data access endpoint for admins, assigned doctors, and the patient themselves.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT])
    @blp.arguments(PatientEmailPathSchema, location="path")
    @blp.doc(
        summary="Obtenir un pacient pel correu",
        description="Els administradors poden obtenir qualsevol pacient; els metges només si hi estan assignats; els pacients poden obtenir el seu propi registre.",
    )
    @blp.response(200, schema=UserResponseSchema, description="Informació del pacient recuperada correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="L'usuari autenticat no pot veure aquest pacient.")
    @blp.response(404, description="Pacient no trobat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(500, description="Error inesperat del servidor en recuperar el pacient.")
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

            factory = AbstractControllerFactory.get_instance()
            patient_controller = factory.get_patient_controller()
            patient = patient_controller.get_patient(patient_email)

            current_user = getattr(g, "current_user", None)
            role_instance = getattr(g, "current_role_instance", None)

            if current_user is None or role_instance is None:
                current_user_email: str = get_jwt_identity()
                user_controller = factory.get_user_controller()
                try:
                    current_user = user_controller.get_user(current_user_email)
                except UserNotFoundException:
                    abort(401, message="Token d'autenticació no vàlid.")
                role_instance = current_user.get_role_instance()

            current_user_email: str = current_user.get_email()

            authorized = (
                current_user_email == patient_email
                or role_instance.doctor_of_this_patient(patient)
            )

            if not authorized:
                abort(403, message="No tens permís per accedir a les dades d'aquest pacient.")

            patient_payload = patient.get_user().to_dict()
            return jsonify(patient_payload), 200

        except UserRoleConflictException as e:
            self.logger.error("User role conflict", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except UserNotFoundException as e:
            self.logger.error("Patient not found", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(404, message=str(e))
        except HTTPException as e:
            self.logger.error("HTTP exception occurred", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            raise e
        except Exception as e:
            self.logger.error("Fetching patient information failed", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(500, message=f"S'ha produït un error inesperat en obtenir el pacient: {str(e)}")

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
        summary="Sol·licitar el restabliment de contrasenya",
        description="Envia un correu amb el codi de restabliment utilitzant la plantilla configurada.",
    )
    @blp.response(200, schema=UserForgotPasswordResponseSchema, description="Correu de restabliment enviat; inclou els minuts de validesa.")
    @blp.response(400, description="Falta un camp obligatori.")
    @blp.response(401, description="Credencials no vàlides per a la sol·licitud de restabliment.")
    @blp.response(404, description="Usuari no trobat per al correu proporcionat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="No s'ha pogut carregar la plantilla o enviar el correu de restabliment.")
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
                abort(500, message="No s'ha pogut carregar la plantilla del correu de restabliment.")

            factory = AbstractForgotPasswordFactory.get_instance()
            forgot_password_facade = factory.get_password_facade()
            forgot_password_facade.process_forgot_password(data['email'], APPLICATION_EMAIL, "Sol·licitud de canvi de contrasenya", template)

            response_payload = {"message": "El mail ha estat enviat exitosament a l'usuari.", "validity": RESET_CODE_VALIDITY_MINUTES}
            return jsonify(response_payload), 200
        
        except SMTPCredentialsException as e:
            self.logger.error("User forgot password failed: SMTP credentials error", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(500, message="Error de configuració del servidor de correu. Contacta amb l'administrador.")
        except SendEmailException as e:
            self.logger.error("User forgot password failed: Email sending error", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(500, message="No s'ha pogut enviar el correu de restabliment. Torna-ho a provar més tard.")
        except UserRoleConflictException as e:
            self.logger.error("User forgot password failed: Role conflict", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except UserNotFoundException as e:
            self.logger.error("User forgot password failed: User not found", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(404, message="No s'ha trobat cap usuari amb el correu proporcionat.")
        except KeyError as e:
            self.logger.error("User forgot password failed due to missing field", module="UserForgotPassword", error=e)
            abort(400, message=f"Falta el camp: {str(e)}")
        except InvalidCredentialsException as e:
            self.logger.error("User forgot password failed: Invalid credentials", module="UserForgotPassword", metadata={"email": data['email']}, error=e)
            abort(401, message=f"Credencials no vàlides: {str(e)}")
        except ValueError as e:
            self.logger.error("User forgot password failed: Value Error", module="UserForgotPassword", error=e)
            abort(422, message=f"Dades no vàlides: {str(e)}")
        except Exception as e:
            self.logger.error("User forgot password failed", module="UserForgotPassword", error=e)
            abort(500, message=f"S'ha produït un error inesperat en sol·licitar el restabliment: {str(e)}")

    @blp.arguments(UserResetPasswordSchema, location='json')
    @blp.doc(
        security=[],
        summary="Restablir la contrasenya amb el codi",
        description="Valida el codi de restabliment i actualitza la contrasenya de l'usuari.",
    )
    @blp.response(200, schema=UserResetPasswordResponseSchema, description="Contrasenya restablerta correctament.")
    @blp.response(400, description="Falta un camp o el codi de restabliment és invàlid o ha caducat.")
    @blp.response(401, description="Credencials no vàlides per a la sol·licitud de restabliment.")
    @blp.response(404, description="Usuari no trobat per al correu proporcionat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en restablir la contrasenya.")
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

            response_payload = {"message": "Contrasenya restablerta correctament."}
            return jsonify(response_payload), 200

        except InvalidResetCodeException as e:
            self.logger.error("User reset password failed: Invalid or expired reset code", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(400, message="El codi de restabliment no és vàlid o ha caducat.")
        except UserRoleConflictException as e:
            self.logger.error("User reset password failed: Role conflict", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except UserNotFoundException as e:
            self.logger.error("User reset password failed: User not found", module="UserForgotPassword", metadata={"email": data.get('email')}, error=e)
            abort(404, message="No s'ha trobat cap usuari amb el correu proporcionat.")
        except KeyError as e:
            self.logger.error("User reset password failed due to missing field", module="UserForgotPassword", error=e)
            abort(400, message=f"Falta el camp: {str(e)}")
        except InvalidCredentialsException as e:
            self.logger.error("User reset password failed: Invalid credentials", module="UserForgotPassword", metadata={"email": data['email']}, error=e)
            abort(401, message=f"Credencials no vàlides: {str(e)}")
        except ValueError as e:
            self.logger.error("User reset password failed: Value Error", module="UserForgotPassword", error=e)
            abort(422, message=f"Dades no vàlides: {str(e)}")
        except Exception as e:
            self.logger.error("User reset password failed", module="UserForgotPassword", error=e)
            abort(500, message=f"S'ha produït un error inesperat en restablir la contrasenya: {str(e)}")
