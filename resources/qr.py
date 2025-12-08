from flask import Response, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import get_jwt_identity

from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.decorators import roles_required
from helpers.enums.user_role import UserRole
from helpers.exceptions.question_exceptions import (
    QuestionCreationException,
    QuestionNotFoundException,
    QuestionUpdateException,
)
from helpers.exceptions.integrity_exceptions import DataIntegrityException
from application.container import ServiceFactory
from schemas import (
    QRGenerateSchema,
    QuestionBulkCreateSchema,
    QuestionIdSchema,
    QuestionPartialUpdateSchema,
    QuestionQuerySchema,
    QuestionResponseSchema,
    QuestionUpdateSchema,
)

blp = Blueprint('qr', __name__, description="Generació de codi QR per obtenir informes de pacients.")


@blp.route('')
class QRResource(MethodView):
    """
    Endpoints per obtenir codis QR.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.PATIENT])
    @blp.arguments(QRGenerateSchema, location='json')
    @blp.doc(
        summary="Obtenir un codi QR per a l'informe mèdic.",
        description="Genera un codi QR que permet obtenir l'informe mèdic d'un pacient.",
    )
    @blp.response(200, description="Codi QR generat correctament.", content_type="image/png")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser pacient per accedir a aquest recurs.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en generar el codi QR.")
    def post(self, data: dict):
        """
        Obté un codi QR per a l'informe mèdic del pacient.
        """
        try:
            pass #TODO: Implementar la generació del codi QR
        except DataIntegrityException as e:
            db.session.rollback()
            self.logger.error("Error d'integritat en generar codi QR", module="QRResource", error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en generar codi QR", module="QRResource", error=e)
            abort(500, message="Error de base de dades en generar el codi QR.")
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en generar codi QR", module="QRResource", error=e)
            abort(500, message=f"S'ha produït un error inesperat en generar el codi QR: {str(e)}")