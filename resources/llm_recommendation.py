from flask import jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import get_jwt_identity

from helpers.debugger.logger import AbstractLogger
from helpers.decorators import roles_required
from helpers.enums.user_role import UserRole
from application.container import ServiceFactory
from helpers.exceptions.llm_exceptions import LLMException
from helpers.exceptions.user_exceptions import UserNotFoundException
from schemas import (
    LlmRecommendationResponse,
)

blp = Blueprint('llm-recommendation', __name__, description="Endpoints per a obtenir recomanacions per un pacient fent servir un LLM.")


@blp.route('')
class LlmRecommendationResource(MethodView):
    """
    Endpoints per obtenir recomanacions per un pacient fent servir un LLM.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.PATIENT])
    @blp.doc(
        summary="Obtenir recomanacions per al pacient.",
        description="Obté recomanacions per a un pacient fent servir un LLM.",
    )
    @blp.response(200, schema=LlmRecommendationResponse, description="Recomanació generada correctament.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="Cal ser pacient per accedir a aquest recurs.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en obtenir la recomanació.")
    def get(self):
        """
        Obtenir una recomanació per a un pacient mitjançant un LLM.
        """
        email:str = None
        try:
            email = get_jwt_identity()

            self.logger.info(
                "Generant recomanació per al pacient",
                module="LlmRecommendationResource",
                metadata={"patient_email": email},
            )

            factory = ServiceFactory.get_instance()
            user_service = factory.build_user_service()
            patient = user_service.get_user(email)
            patient_data = user_service.get_patient_data(patient, patient, graph_format="png")
            recommendation_service = factory.build_recommendation_service()
            recommendation = recommendation_service.get_recommendation_for_patient(patient_data)

            if isinstance(recommendation, dict) and "error" in recommendation:
                self.logger.error(
                    "Error en obtenir recomanació del LLM",
                    module="LlmRecommendationResource",
                    metadata={"patient_email": email},
                )
                raise LLMException(recommendation["error"])
            return jsonify(recommendation), 200
        except UserNotFoundException as e:
            self.logger.error(
                "Pacient no trobat en generar recomanació",
                module="LlmRecommendationResource",
                metadata={"patient_email": email},
                error=e,
            )
            abort(404, message=str(e))
        except LLMException as e:
            self.logger.error(
                "Error del LLM en generar recomanació",
                module="LlmRecommendationResource",
                metadata={"patient_email": email},
                error=e,
            )
            abort(500, message=f"S'ha produït un error en generar la recomanació: {str(e)}")
        except Exception as e:
            self.logger.error("Error inesperat en recuperar recomanacions", module="LlmRecommendationResource", error=e)
            abort(500, message=f"S'ha produït un error inesperat en generar la recomanació: {str(e)}")