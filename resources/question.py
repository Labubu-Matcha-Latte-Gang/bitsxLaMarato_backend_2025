from flask import Response, jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.decorators import roles_required
from helpers.enums.user_role import UserRole
from helpers.exceptions.question_exceptions import (
    QuestionCreationException,
    QuestionNotFoundException,
    QuestionUpdateException,
)
from helpers.factories.controller_factories import AbstractControllerFactory
from schemas import (
    QuestionBulkCreateSchema,
    QuestionIdSchema,
    QuestionPartialUpdateSchema,
    QuestionQuerySchema,
    QuestionResponseSchema,
    QuestionUpdateSchema,
)

blp = Blueprint('question', __name__, description="Operacions CRUD per a les preguntes de l'aplicació.")


@blp.route('')
class QuestionResource(MethodView):
    """
    Endpoints per gestionar preguntes.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.ADMIN])
    @blp.arguments(QuestionBulkCreateSchema, location='json')
    @blp.doc(
        summary="Crear preguntes",
        description="Crea múltiples preguntes en un sol pas.",
    )
    @blp.response(201, schema=QuestionResponseSchema(many=True), description="Preguntes creades correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en crear les preguntes.")
    def post(self, data: dict):
        """
        Crear un conjunt de preguntes.

        Requereix un array 'questions' amb camps text, question_type i difficulty.
        """
        try:
            questions_data = data.get('questions', [])
            self.logger.info(
                "Creant preguntes",
                module="QuestionResource",
                metadata={"count": len(questions_data)},
            )

            factory = AbstractControllerFactory.get_instance()
            question_controller = factory.get_question_controller()

            questions = question_controller.create_questions(questions_data)
            for question in questions:
                db.session.add(question)
            db.session.commit()

            return jsonify([question.to_dict() for question in questions]), 201
        except (QuestionCreationException, ValueError) as e:
            db.session.rollback()
            self.logger.error(
                "Error de validació en crear preguntes",
                module="QuestionResource",
                metadata={"count": len(data.get('questions', []))},
                error=e,
            )
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en crear preguntes", module="QuestionResource", error=e)
            abort(500, message="Error de base de dades en crear les preguntes.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en crear preguntes", module="QuestionResource", error=e)
            abort(500, message=f"S'ha produït un error inesperat en crear les preguntes: {str(e)}")

    @roles_required([UserRole.ADMIN])
    @blp.arguments(QuestionQuerySchema, location='query')
    @blp.doc(
        summary="Consultar preguntes",
        description=(
            "Filtra preguntes per diversos criteris: "
            "`id` (UUID exacte), `question_type` (enum), `difficulty` (valor exacte), "
            "`difficulty_min` (>=) i `difficulty_max` (<=). "
            "Es poden combinar; sense cap filtre es retornen totes."
        ),
    )
    @blp.response(200, schema=QuestionResponseSchema(many=True), description="Preguntes recuperades correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat la pregunta indicada.")
    @blp.response(500, description="Error inesperat del servidor en consultar les preguntes.")
    def get(self, query_args: dict):
        """
        Obtenir preguntes amb filtres opcionals.

        Paràmetres de consulta:
        - `id`: UUID exacte d'una pregunta (retorna només aquesta o 404 si no existeix).
        - `question_type`: Valor de l'enum QuestionType.
        - `difficulty`: Valor exacte de dificultat (0-5).
        - `difficulty_min`: Dificultat mínima (>=).
        - `difficulty_max`: Dificultat màxima (<=).

        Es poden combinar `difficulty`, `difficulty_min` i `difficulty_max`; tots els filtres aplicats alhora.
        Sense filtres retorna totes les preguntes.
        """
        filters = {k: v for k, v in (query_args or {}).items() if v is not None}
        try:
            self.logger.info(
                "Recuperant preguntes",
                module="QuestionResource",
                metadata={"filters": filters},
            )

            factory = AbstractControllerFactory.get_instance()
            question_controller = factory.get_question_controller()
            questions = question_controller.list_questions(filters)

            return jsonify([question.to_dict() for question in questions]), 200
        except QuestionNotFoundException as e:
            self.logger.error(
                "Pregunta no trobada",
                module="QuestionResource",
                metadata={"filters": filters},
                error=e,
            )
            abort(404, message=str(e))
        except Exception as e:
            self.logger.error("Error inesperat en recuperar preguntes", module="QuestionResource", error=e)
            abort(500, message=f"S'ha produït un error inesperat en recuperar les preguntes: {str(e)}")

    @roles_required([UserRole.ADMIN])
    @blp.arguments(QuestionUpdateSchema, location='json')
    @blp.doc(
        summary="Reemplaçar una pregunta",
        description="Actualitza tots els camps d'una pregunta existent.",
    )
    @blp.response(200, schema=QuestionResponseSchema, description="Pregunta actualitzada correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat la pregunta indicada.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en actualitzar la pregunta.")
    def put(self, data: dict):
        """
        Reemplaçar completament una pregunta.

        Cal passar l'ID per query string (?id=<uuid>) i tots els camps al cos.
        """
        question_id = None
        try:
            query_args:dict = QuestionIdSchema().load(request.args)
            question_id = query_args['id']
        except ValidationError as e:
            abort(422, message=e.messages)

        try:
            self.logger.info(
                "Actualitzant pregunta (PUT)",
                module="QuestionResource",
                metadata={"question_id": str(question_id)},
            )

            factory = AbstractControllerFactory.get_instance()
            question_controller = factory.get_question_controller()
            question = question_controller.update_question(question_id, data)

            db.session.commit()
            return jsonify(question.to_dict()), 200
        except QuestionNotFoundException as e:
            db.session.rollback()
            self.logger.error("Pregunta no trobada en PUT", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(404, message=str(e))
        except QuestionUpdateException as e:
            db.session.rollback()
            self.logger.error("Error de validació en PUT de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en PUT de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(500, message="Error de base de dades en actualitzar la pregunta.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en PUT de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(500, message=f"S'ha produït un error inesperat en actualitzar la pregunta: {str(e)}")

    @roles_required([UserRole.ADMIN])
    @blp.arguments(QuestionPartialUpdateSchema, location='json')
    @blp.doc(
        summary="Actualització parcial d'una pregunta",
        description="Actualitza només els camps indicats d'una pregunta existent.",
    )
    @blp.response(200, schema=QuestionResponseSchema, description="Pregunta actualitzada parcialment.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat la pregunta indicada.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en actualitzar la pregunta.")
    def patch(self, data: dict):
        """
        Actualitzar parcialment una pregunta.

        Cal passar l'ID per query string (?id=<uuid>) i com a mínim un camp al cos.
        """
        question_id = None
        try:
            query_args:dict = QuestionIdSchema().load(request.args)
            question_id = query_args['id']
        except ValidationError as e:
            abort(422, message=e.messages)

        if not data:
            abort(400, message="No s'ha proporcionat cap camp per actualitzar.")

        try:
            self.logger.info(
                "Actualitzant pregunta (PATCH)",
                module="QuestionResource",
                metadata={"question_id": str(question_id), "fields": list(data.keys())},
            )

            factory = AbstractControllerFactory.get_instance()
            question_controller = factory.get_question_controller()
            question = question_controller.update_question(question_id, data)

            db.session.commit()
            return jsonify(question.to_dict()), 200
        except QuestionNotFoundException as e:
            db.session.rollback()
            self.logger.error("Pregunta no trobada en PATCH", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(404, message=str(e))
        except QuestionUpdateException as e:
            db.session.rollback()
            self.logger.error("Error de validació en PATCH de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en PATCH de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(500, message="Error de base de dades en actualitzar la pregunta.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en PATCH de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(500, message=f"S'ha produït un error inesperat en actualitzar la pregunta: {str(e)}")

    @roles_required([UserRole.ADMIN])
    @blp.doc(
        summary="Eliminar una pregunta",
        description="Esborra una pregunta existent identificada per ID.",
    )
    @blp.response(204, description="Pregunta eliminada correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser administrador per accedir a aquest recurs.")
    @blp.response(404, description="No s'ha trobat la pregunta indicada.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en eliminar la pregunta.")
    def delete(self):
        """
        Eliminar una pregunta pel seu ID.
        """
        question_id = None
        try:
            query_args:dict = QuestionIdSchema().load(request.args)
            question_id = query_args['id']
        except ValidationError as e:
            abort(422, message=e.messages)

        try:
            self.logger.info(
                "Eliminant pregunta",
                module="QuestionResource",
                metadata={"question_id": str(question_id)},
            )

            factory = AbstractControllerFactory.get_instance()
            question_controller = factory.get_question_controller()

            question = question_controller.delete_question(question_id)
            db.session.delete(question)
            db.session.commit()

            return Response(status=204)
        except QuestionNotFoundException as e:
            db.session.rollback()
            self.logger.error("Pregunta no trobada en DELETE", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(404, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en DELETE de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(500, message="Error de base de dades en eliminar la pregunta.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en DELETE de pregunta", module="QuestionResource", metadata={"question_id": str(question_id)}, error=e)
            abort(500, message=f"S'ha produït un error inesperat en eliminar la pregunta: {str(e)}")
