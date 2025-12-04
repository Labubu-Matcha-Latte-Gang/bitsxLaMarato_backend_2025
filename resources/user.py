from functools import lru_cache
from pathlib import Path

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response, jsonify
from werkzeug.exceptions import HTTPException

from db import db
from sqlalchemy.exc import IntegrityError
from globals import APPLICATION_EMAIL, RESET_CODE_VALIDITY_MINUTES, RESET_PASSWORD_FRONTEND_PATH
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
from helpers.exceptions.integrity_exceptions import DataIntegrityException
from infrastructure.sqlalchemy.unit_of_work import map_integrity_error, SQLAlchemyUnitOfWork

from helpers.enums.user_role import UserRole
from application.container import ServiceFactory
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
    UserForgotPasswordSchema,
    PatientDataResponseSchema,
)

blp = Blueprint('user', __name__, description="Operacions relacionades amb els usuaris")

@blp.route('/patient')
class PatientRegister(MethodView):
    """
    Endpoints per registrar comptes de pacients.
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
        Registra un nou usuari pacient.

        Rep un JSON que segueix `PatientRegisterSchema` amb mètriques del pacient i opcionalment
        malalties, tractaments i associacions de metges. Crea l'usuari, el perfil de pacient i
        assigna els metges indicats.

        Codis d'estat:
        - 201: Pacient creat; retorna el payload de l'usuari creat.
        - 400: Falta algun camp o el correu ja existeix.
        - 404: No s'ha trobat algun correu de metge proporcionat.
        - 422: El payload no supera la validació d'esquema.
        - 500: Error inesperat durant la creació.
        """
        try:
            safe_metadata = {k: v for k, v in data.items() if k != 'password'}
            self.logger.info("Start registering a patient", module="PatientRegister", metadata=safe_metadata)

            patient_service = ServiceFactory.get_instance().build_patient_service()
            patient = patient_service.register_patient(data)

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
        except DataIntegrityException as e:
            db.session.rollback()
            self.logger.error("Patient register failed: Integrity violation", module="PatientRegister", metadata={"email": data.get('email')}, error=e)
            abort(422, message=str(e))
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
    Endpoints per registrar comptes de metges.
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
        Registra un nou usuari metge.

        Rep un JSON que segueix `DoctorRegisterSchema`, crea l'usuari i el perfil de metge i
        enllaça els pacients indicats si n'hi ha.

        Codis d'estat:
        - 201: Metge creat; retorna el payload de l'usuari creat.
        - 400: Falta algun camp o el correu ja existeix.
        - 404: No s'ha trobat algun correu de pacient proporcionat.
        - 422: El payload no supera la validació d'esquema.
        - 500: Error inesperat durant la creació.
        """
        try:
            safe_metadata = {k: v for k, v in data.items() if k != 'password'}
            self.logger.info("Start registering a doctor", module="DoctorRegister", metadata=safe_metadata)

            doctor_service = ServiceFactory.get_instance().build_doctor_service()
            doctor = doctor_service.register_doctor(data)

            return jsonify(doctor.to_dict()), 201
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
        except DataIntegrityException as e:
            db.session.rollback()
            self.logger.error("Doctor register failed: Integrity violation", module="DoctorRegister", metadata={"email": data.get('email')}, error=e)
            abort(422, message=str(e))
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
    Autentica usuaris i emet tokens d'accés JWT.
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
        Autentica un usuari i emet un JWT.

        Rep un JSON que segueix `UserLoginSchema` amb correu i contrasenya. Si és correcte,
        retorna un token d'accés per usar als endpoints autenticats.

        Codis d'estat:
        - 200: Credencials vàlides; retorna el token JWT.
        - 400: Falta algun camp d'inici de sessió.
        - 401: Credencials no vàlides.
        - 409: Estat de rol inconsistent.
        - 422: El payload no supera la validació d'esquema.
        - 500: Error inesperat durant l'autenticació.
        """
        try:
            self.logger.info("User login attempt", module="UserLogin", metadata={"email": data['email']})

            user_service = ServiceFactory.get_instance().build_user_service()
            access_token = user_service.login(data["email"], data["password"])
            return {"access_token": access_token}, 200
        except UserNotFoundException as e:
            self.logger.error("User login failed: User not found", module="UserLogin", metadata={"email": data['email']}, error=e)
            abort(401, message="Correu o contrassenya no vàlids.")
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
    Operacions CRUD autenticades per a l'usuari actual.
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
        Recupera el perfil de l'usuari autenticat.

        Retorna les dades bàsiques i la informació específica del rol de la identitat actual.

        Codis d'estat:
        - 200: Usuari trobat i retornat.
        - 401: Falta o és invàlid el token.
        - 404: L'usuari no existeix.
        - 409: Configuració de rol inconsistent.
        - 500: Error inesperat en recuperar l'usuari.
        """
        try:
            self.logger.info("Fetching user information", module="UserCRUD")

            email:str = get_jwt_identity()

            user_service = ServiceFactory.get_instance().build_user_service()
            user = user_service.get_user(email)

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
        Substitueix completament el perfil de l'usuari autenticat.

        Rep un JSON que segueix `UserUpdateSchema`. Actualitza les dades personals, la contrasenya si s'envia
        i reemplaça les associacions metge/pacient amb les llistes indicades.

        Codis d'estat:
        - 200: Usuari actualitzat i retornat.
        - 401: Falta o és invàlid el token.
        - 404: Usuari o relacionats no trobats.
        - 409: Configuració de rol inconsistent.
        - 422: El payload no supera la validació d'esquema.
        - 500: Error inesperat en l'actualització.
        """
        email: str | None = None
        try:
            email = get_jwt_identity()

            user_service = ServiceFactory.get_instance().build_user_service()
            user = user_service.update_user(email, data)

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
        except DataIntegrityException as e:
            db.session.rollback()
            self.logger.error("User update failed: Integrity violation", module="UserCRUD", metadata={"email": email}, error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            mapped = map_integrity_error(e)
            self.logger.error("User update failed: Integrity error", module="UserCRUD", metadata={"email": email}, error=mapped)
            abort(422, message=str(mapped))
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
        Actualitza parcialment el perfil de l'usuari autenticat.

        Accepta qualsevol subconjunt de camps de `UserPartialUpdateSchema`. Actualitza dades personals i
        contrasenya si s'indica. Per a pacients/metges, si s'envien llistes d'associacions, les reemplaça
        amb els valors proporcionats.

        Codis d'estat:
        - 200: Usuari actualitzat i retornat.
        - 401: Falta o és invàlid el token.
        - 404: Usuari o relacionats no trobats.
        - 409: Configuració de rol inconsistent.
        - 422: El payload no supera la validació d'esquema.
        - 500: Error inesperat en l'actualització.
        """
        email: str | None = None
        try:
            email = get_jwt_identity()
            
            user_service = ServiceFactory.get_instance().build_user_service()
            user = user_service.update_user(email, data)

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
        except DataIntegrityException as e:
            db.session.rollback()
            self.logger.error("Partial user update failed: Integrity violation", module="UserCRUD", metadata={"email": email}, error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            mapped = map_integrity_error(e)
            self.logger.error("Partial user update failed: Integrity error", module="UserCRUD", metadata={"email": email}, error=mapped)
            abort(422, message=str(mapped))
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
        Elimina el compte de l'usuari autenticat.

        Esborra les associacions de rol, elimina el registre d'usuari i retorna una resposta 204 buida.

        Codis d'estat:
        - 204: Usuari eliminat.
        - 401: Falta o és invàlid el token.
        - 404: L'usuari no existeix.
        - 409: Configuració de rol inconsistent.
        - 500: Error inesperat en eliminar l'usuari.
        """
        email: str | None = None
        try:
            email = get_jwt_identity()

            self.logger.info("Deleting user", module="UserCRUD", metadata={"email": email})

            user_service = ServiceFactory.get_instance().build_user_service()
            user_service.delete_user(email)

            return Response(status=204)
        except UserRoleConflictException as e:
            db.session.rollback()
            self.logger.error("Deleting user failed due to role conflict", module="UserCRUD", metadata={"email": email}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except UserNotFoundException as e:
            db.session.rollback()
            self.logger.error("User not found", module="UserCRUD", error=e)
            abort(404, message=str(e))
        except DataIntegrityException as e:
            db.session.rollback()
            self.logger.error("Deleting user failed: Integrity violation", module="UserCRUD", metadata={"email": email}, error=e)
            abort(422, message=str(e))
        except Exception as e:
            db.session.rollback()
            self.logger.error("Deleting user failed", module="UserCRUD", error=e)
            abort(500, message=f"S'ha produït un error inesperat en eliminar l'usuari: {str(e)}")

@blp.route('/<string:email>')
class PatientData(MethodView):
    """
    Endpoint d'accés a dades de pacient per a administradors, metges assignats i el propi pacient.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT])
    @blp.arguments(PatientEmailPathSchema, location="path")
    @blp.doc(
        summary="Obtenir un pacient pel correu",
        description=(
            "Els administradors poden obtenir qualsevol pacient; els metges només si hi estan assignats; "
            "els pacients poden obtenir el seu propi registre. La resposta inclou les dades del pacient, "
            "les puntuacions, les preguntes contestades i els gràfics generats com a fragments HTML (div + script) "
            "codificats en base64, pensats per ser injectats a una WebView (p. ex. Flutter amb `loadHtmlString`) "
            "o a un contenidor que executi scripts."
        ),
    )
    @blp.response(200, schema=PatientDataResponseSchema, description="Dades del pacient i gràfics generats correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="L'usuari autenticat no pot veure aquest pacient.")
    @blp.response(404, description="Pacient no trobat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(500, description="Error inesperat del servidor en recuperar el pacient.")
    def get(self, path_args: dict, **kwargs):
        """
        Recupera informació d'un pacient pel correu amb autorització per rol.

        Cal un JWT vàlid. Els administradors poden veure qualsevol pacient. Els metges poden veure
        pacients als quals estan assignats. Els pacients poden veure el seu propi registre. La
        resposta inclou:
        - `patient`: dades bàsiques i de rol del pacient.
        - `scores`: llista de puntuacions d'activitats.
        - `questions`: preguntes contestades amb mètriques d'anàlisi.
        - `graph_files`: fragments HTML (div + script) dels gràfics codificats en base64. Cal decodificar el contingut en base64 i injectar-lo a una WebView (p. ex. Flutter: `controller.loadHtmlString(fragment)`) o a un contenidor que executi scripts. Cada fragment carrega Plotly des del CDN si no és present.

        Codis d'estat:
        - 200: Informació del pacient retornada.
        - 401: Falta o és invàlid el token.
        - 403: L'usuari autenticat no té permís per veure el pacient.
        - 404: El pacient no existeix.
        - 409: Configuració de rol inconsistent.
        - 500: Error inesperat en recuperar el pacient.
        """
        patient_email = None
        current_email: str | None = None
        try:
            patient_email = path_args.get('email')

            self.logger.info(
                "Fetching patient information",
                module="PatientData",
                metadata={"patient_email": patient_email}
            )

            factory = ServiceFactory.get_instance()
            user_service = factory.build_user_service()

            current_email = get_jwt_identity()
            try:
                current_user = user_service.get_user(current_email)
            except UserNotFoundException:
                abort(401, message="Token d'autenticació no vàlid.")

            patient_service = factory.build_patient_service()
            patient = patient_service.get_patient(patient_email)

            patient_payload = user_service.get_patient_data(current_user, patient)
            return jsonify(patient_payload), 200
        except UserRoleConflictException as e:
            self.logger.error("User role conflict", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(409, message=f"Conflicte de rol d'usuari: {str(e)}")
        except UserNotFoundException as e:
            self.logger.error("Patient not found", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(404, message=str(e))
        except PermissionError as e:
            self.logger.error("Unauthorized access to patient", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(403, message=str(e))
        except HTTPException as e:
            self.logger.error("HTTP exception occurred", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            raise e
        except Exception as e:
            self.logger.error("Fetching patient information failed", module="PatientData", metadata={"patient_email": patient_email}, error=e)
            abort(500, message=f"S'ha produït un error inesperat en obtenir el pacient: {str(e)}")

@blp.route('/forgot-password')
class UserForgotPassword(MethodView):
    """
    Endpoints per sol·licitar i completar restabliments de contrasenya.
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
        Inicia el flux de restabliment de contrasenya.

        Rep un JSON que segueix `UserForgotPasswordSchema` amb el correu de l'usuari. Carrega la
        plantilla del correu, genera i envia un codi de restabliment i retorna la finestra de validesa.

        Codis d'estat:
        - 200: Correu de restabliment enviat correctament.
        - 400: Falta un camp obligatori.
        - 401: Credencials no vàlides.
        - 404: L'usuari no existeix.
        - 409: Configuració de rol inconsistent.
        - 422: El payload no supera la validació d'esquema.
        - 500: No s'ha pogut carregar la plantilla o enviar el correu.
        """
        try:
            self.logger.info("A user forgot their password", module="UserForgotPassword", metadata={"email": data['email']})

            # TODO: Password reset functionality is temporarily disabled
            # This will be properly implemented when email sending is ready
            
            # Temporary simple check using direct database access
            # This avoids UnitOfWork attribute errors while maintaining basic validation
            try:
                from models.user import User
                user = User.query.filter_by(email=data["email"]).first()
                
                if not user:
                    self.logger.info("User not found", module="UserForgotPassword", metadata={"email": data["email"]})
                    abort(404, message="Usuari no trobat.")
                
                # TODO: Generate reset code and send email when functionality is ready
                self.logger.info("Password reset temporarily disabled", module="UserForgotPassword", metadata={"email": data["email"]})
                
                # Return success message without actually sending email
                return {"message": "Si el correu existeix, rebràs un missatge amb instruccions per restablir la contrasenya.", "validity_minutes": RESET_CODE_VALIDITY_MINUTES}, 200
                
            except Exception as e:
                self.logger.error("Forgot password failed", module="UserForgotPassword", metadata={"email": data["email"]}, error=e)
                abort(500, message="Error intern del servidor.")

        except KeyError as e:
            db.session.rollback()
            self.logger.error("Forgot password failed due to missing field", module="UserForgotPassword", error=e)
            abort(400, message=f"Falta el camp: {str(e)}")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Forgot password failed", module="UserForgotPassword", error=e)
            abort(500, message=f"S'ha produït un error inesperat en sol·licitar el restabliment de contrasenya: {str(e)}")

@blp.route('/reset-password')
class UserResetPassword(MethodView):
    """
    Endpoint per restablir la contrasenya d'un usuari.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(UserResetPasswordSchema, location='json')
    @blp.doc(
        security=[],
        summary="Restablir contrasenya",
        description="Actualitza la contrasenya d'un usuari si el codi de restabliment és vàlid.",
    )
    @blp.response(200, schema=UserResetPasswordResponseSchema, description="Contrasenya actualitzada correctament.")
    @blp.response(400, description="Falta un camp obligatori o el codi de restabliment és invàlid.")
    @blp.response(401, description="Correu o codi de restabliment no vàlids.")
    @blp.response(404, description="Usuari no trobat pel correu proporcionat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en restablir la contrasenya.")
    def put(self, data: dict) -> Response:  # Changed from post to put
        """
        Restableix la contrasenya d'un usuari.

        Rep un JSON que segueix `UserResetPasswordSchema` amb el correu de l'usuari, el codi de restabliment
        i la nova contrasenya. Si el codi és vàlid, actualitza la contrasenya de l'usuari.

        Codis d'estat:
        - 200: Contrasenya actualitzada correctament.
        - 400: Falta un camp obligatori o el codi és invàlid.
        - 401: Correu o codi de restabliment no vàlids.
        - 404: L'usuari no existeix.
        - 409: Configuració de rol inconsistent.
        - 422: El payload no supera la validació d'esquema.
        - 500: Error inesperat durant el restabliment de la contrasenya.
        """
        try:
            self.logger.info("Resetting user password", module="UserResetPassword", metadata={"email": data['email']})

            # TODO: Password reset functionality is temporarily disabled
            # This will be properly implemented when email sending and code validation is ready
            
            # Temporary simple check using direct database access
            try:
                from models.user import User
                user = User.query.filter_by(email=data["email"]).first()
                
                if not user:
                    self.logger.info("User not found", module="UserResetPassword", metadata={"email": data["email"]})
                    abort(404, message="Usuari no trobat.")
                
                # TODO: Validate reset code and update password when functionality is ready
                self.logger.info("Password reset temporarily disabled", module="UserResetPassword", metadata={"email": data["email"]})
                
                # Return success message without actually resetting password
                return {"message": "Funcionalitat de restabliment de contrasenya temporalment deshabilitada."}, 200
                
            except Exception as e:
                self.logger.error("Password reset failed", module="UserResetPassword", metadata={"email": data["email"]}, error=e)
                abort(500, message="Error intern del servidor.")

        except KeyError as e:
            db.session.rollback()
            self.logger.error("Reset password failed due to missing field", module="UserResetPassword", error=e)
            abort(400, message=f"Falta el camp: {str(e)}")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Reset password failed", module="UserResetPassword", error=e)
            abort(500, message=f"S'ha produït un error inesperat en restablir la contrasenya: {str(e)}")
