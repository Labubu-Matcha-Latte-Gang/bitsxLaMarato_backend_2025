from flask import Response, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import get_jwt_identity

from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.decorators import roles_required
from helpers.enums.user_role import UserRole
from helpers.exceptions.activity_exceptions import (
    ActivityCreationException,
    ActivityNotFoundException,
    ActivityUpdateException,
)
from application.container import ServiceFactory
from schemas import (
    ActivityBulkCreateSchema,
    ActivityIdSchema,
    ActivityPartialUpdateSchema,
    ActivityQuerySchema,
    ActivityResponseSchema,
    ActivityUpdateSchema,
)

blp = Blueprint('activity', __name__, description="Operacions CRUD per a les activitats de l'aplicació.")


@blp.route('')
class ActivityResource(MethodView):
    """
    Endpoints per gestionar activitats.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.ADMIN])
    @blp.arguments(ActivityBulkCreateSchema, location='json')
    @blp.doc(
        summary="Crear activitats",
        description="Crea múltiples activitats en un sol pas.",
    )
    @blp.response(201, schema=ActivityResponseSchema(many=True), description="Activitats creades correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en crear les activitats.")
    def post(self, data: dict):
        """
        Crear un conjunt d'activitats.

        Requereix un array 'activities' amb camps title, description, activity_type i difficulty.
        """
        try:
            activities_data = data.get('activities', [])
            self.logger.info(
                "Creant activitats",
                module="ActivityResource",
                metadata={"count": len(activities_data)},
            )

            activity_service = ServiceFactory().build_activity_service()

            activities = activity_service.create_activities(activities_data)

            return jsonify([activity.to_dict() for activity in activities]), 201
        except (ActivityCreationException, ValueError) as e:
            db.session.rollback()
            self.logger.error(
                "Error de validacio en crear activitats",
                module="ActivityResource",
                metadata={"count": len(data.get('activities', []))},
                error=e,
            )
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en crear activitats", module="ActivityResource", error=e)
            abort(500, message="Error de base de dades en crear les activitats.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en crear activitats", module="ActivityResource", error=e)
            abort(500, message=f"S'ha produit un error inesperat en crear les activitats: {str(e)}")

    @roles_required([UserRole.ADMIN, UserRole.PATIENT])
    @blp.arguments(ActivityQuerySchema, location='query')
    @blp.doc(
        summary="Consultar activitats",
        description=(
            "Filtra activitats per diversos criteris: "
            "`id` (UUID exacte), `title` (text exacte), `activity_type` (enum), `difficulty` (valor exacte), "
            "`difficulty_min` (>=) i `difficulty_max` (<=). "
            "Es poden combinar; sense cap filtre es retornen totes."
        ),
    )
    @blp.response(200, schema=ActivityResponseSchema(many=True), description="Activitats recuperades correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador o pacient per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat l'activitat indicada.")
    @blp.response(500, description="Error inesperat del servidor en consultar les activitats.")
    def get(self, query_args: dict):
        """
        Obtenir activitats amb filtres opcionals.

        Paràmetres de consulta:
        - `id`: UUID exacte d'una activitat (retorna només aquesta o 404 si no existeix).
        - `title`: Títol exacte de l'activitat.
        - `activity_type`: Valor de l'enum QuestionType.
        - `difficulty`: Valor exacte de dificultat (0-5).
        - `difficulty_min`: Dificultat mínima (>=).
        - `difficulty_max`: Dificultat màxima (<=).

        Es poden combinar `difficulty`, `difficulty_min` i `difficulty_max`; tots els filtres aplicats alhora.
        Sense filtres retorna totes les activitats.
        """
        filters = {k: v for k, v in (query_args or {}).items() if v is not None}
        try:
            self.logger.info(
                "Recuperant activitats",
                module="ActivityResource",
                metadata={"filters": filters},
            )

            activity_service = ServiceFactory().build_activity_service()
            activities = activity_service.list_activities(filters)

            return jsonify([activity.to_dict() for activity in activities]), 200
        except ActivityNotFoundException as e:
            self.logger.error(
                "Activitat no trobada",
                module="ActivityResource",
                metadata={"filters": filters},
                error=e,
            )
            abort(404, message=str(e))
        except Exception as e:
            self.logger.error("Error inesperat en recuperar activitats", module="ActivityResource", error=e)
            abort(500, message=f"S'ha produit un error inesperat en recuperar les activitats: {str(e)}")

    @roles_required([UserRole.ADMIN])
    @blp.arguments(ActivityIdSchema, location='query')
    @blp.arguments(ActivityUpdateSchema, location='json')
    @blp.doc(
        summary="Reemplaçar una activitat",
        description="Actualitza tots els camps d'una activitat existent.",
    )
    @blp.response(200, schema=ActivityResponseSchema, description="Activitat actualitzada correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat l'activitat indicada.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en actualitzar l'activitat.")
    def put(self, query_args: dict, data: dict):
        """
        Reemplaçar completament una activitat.

        Cal passar l'ID per query string (?id=<uuid>) i tots els camps al cos.
        """
        activity_id = query_args['id']

        try:
            self.logger.info(
                "Actualitzant activitat (PUT)",
                module="ActivityResource",
                metadata={"activity_id": str(activity_id)},
            )

            activity_service = ServiceFactory().build_activity_service()
            activity = activity_service.update_activity(activity_id, data)

            return jsonify(activity.to_dict()), 200
        except ActivityNotFoundException as e:
            db.session.rollback()
            self.logger.error("Activitat no trobada en PUT", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(404, message=str(e))
        except ActivityUpdateException as e:
            db.session.rollback()
            self.logger.error("Error de validacio en PUT d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en PUT d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(500, message="Error de base de dades en actualitzar l'activitat.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en PUT d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(500, message=f"S'ha produit un error inesperat en actualitzar l'activitat: {str(e)}")

    @roles_required([UserRole.ADMIN])
    @blp.arguments(ActivityIdSchema, location='query')
    @blp.arguments(ActivityPartialUpdateSchema, location='json')
    @blp.doc(
        summary="Actualitzacio parcial d'una activitat",
        description="Actualitza nomes els camps indicats d'una activitat existent.",
    )
    @blp.response(200, schema=ActivityResponseSchema, description="Activitat actualitzada parcialment.")
    @blp.response(401, description="Falta o es invalid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat l'activitat indicada.")
    @blp.response(422, description="El cos de la sollicitud no ha superat la validacio.")
    @blp.response(500, description="Error inesperat del servidor en actualitzar l'activitat.")
    def patch(self, query_args: dict, data: dict):
        """
        Actualitzar parcialment una activitat.

        Cal passar l'ID per query string (?id=<uuid>) i com a minim un camp al cos.
        """
        activity_id = query_args['id']

        if not data:
            abort(400, message="No s'ha proporcionat cap camp per actualitzar.")

        try:
            self.logger.info(
                "Actualitzant activitat (PATCH)",
                module="ActivityResource",
                metadata={"activity_id": str(activity_id), "fields": list(data.keys())},
            )

            activity_service = ServiceFactory().build_activity_service()
            activity = activity_service.update_activity(activity_id, data)

            return jsonify(activity.to_dict()), 200
        except ActivityNotFoundException as e:
            db.session.rollback()
            self.logger.error("Activitat no trobada en PATCH", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(404, message=str(e))
        except ActivityUpdateException as e:
            db.session.rollback()
            self.logger.error("Error de validacio en PATCH d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en PATCH d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(500, message="Error de base de dades en actualitzar l'activitat.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en PATCH d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(500, message=f"S'ha produit un error inesperat en actualitzar l'activitat: {str(e)}")

    @roles_required([UserRole.ADMIN])
    @blp.arguments(ActivityIdSchema, location='query')
    @blp.doc(
        summary="Eliminar una activitat",
        description="Esborra una activitat existent identificada per ID.",
    )
    @blp.response(204, description="Activitat eliminada correctament.")
    @blp.response(401, description="Falta o es invalid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat l'activitat indicada.")
    @blp.response(422, description="El cos de la sollicitud no ha superat la validacio.")
    @blp.response(500, description="Error inesperat del servidor en eliminar l'activitat.")
    def delete(self, query_args: dict):
        """
        Eliminar una activitat pel seu ID.
        """
        activity_id = query_args['id']

        try:
            self.logger.info(
                "Eliminant activitat",
                module="ActivityResource",
                metadata={"activity_id": str(activity_id)},
            )

            activity_service = ServiceFactory().build_activity_service()
            activity_service.delete_activity(activity_id)

            return Response(status=204)
        except ActivityNotFoundException as e:
            db.session.rollback()
            self.logger.error("Activitat no trobada en DELETE", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(404, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en DELETE d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(500, message="Error de base de dades en eliminar l'activitat.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en DELETE d'activitat", module="ActivityResource", metadata={"activity_id": str(activity_id)}, error=e)
            abort(500, message=f"S'ha produit un error inesperat en eliminar l'activitat: {str(e)}")


@blp.route('/recommended')
class RecommendedActivityResource(MethodView):
    """
    Endpoints per a les activitats recomanades.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.PATIENT])
    @blp.doc(
        summary="Obtenir activitats recomanades",
        description=(
            "Obte una activitat recomanada per al pacient."
        ),
    )
    @blp.response(200, schema=ActivityResponseSchema, description="Activitat recomanada recuperada correctament.")
    @blp.response(401, description="Falta o es invalid el JWT.")
    @blp.response(403, description="Cal ser pacient per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat l'activitat indicada.")
    @blp.response(500, description="Error inesperat del servidor en consultar les activitats.")
    def get(self):
        """
        Obtenir una activitat recomanada.
        """
        email: str | None = None
        try:
            email = get_jwt_identity()

            self.logger.info(
                "Recuperant activitat recomanada",
                module="RecommendedActivityResource",
                metadata={"patient_email": email},
            )

            factory = ServiceFactory()
            user_service = factory.build_user_service()
            patient = user_service.get_user(email)

            activity_service = factory.build_activity_service()
            activity = activity_service.get_recommended(patient)  # type: ignore[arg-type]

            return jsonify(activity.to_dict()), 200
        except ActivityNotFoundException as e:
            self.logger.error(
                "Activitat no trobada",
                module="RecommendedActivityResource",
                metadata={"patient_email": email},
                error=e,
            )
            abort(404, message=str(e))
        except Exception as e:
            self.logger.error("Error inesperat en recuperar activitats", module="RecommendedActivityResource", error=e)
            abort(500, message=f"S'ha produit un error inesperat en recuperar les activitats recomanades: {str(e)}")
