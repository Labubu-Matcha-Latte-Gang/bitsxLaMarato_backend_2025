import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response

from helpers.debugger.logger import AbstractLogger

blp = Blueprint('health', __name__, description="Obtenir l'estat de salut de l'API.")

@blp.route('')
class Health(MethodView):
    """Prova de vida lleugera de l'API."""

    logger = AbstractLogger.get_instance()

    @blp.doc(
        security=[],
        summary="Prova de salut",
        description="Retorna 200 quan el servei és accessible.",
    )
    @blp.response(200, description="Servei accessible.")
    @blp.response(500, description="Error inesperat del servidor durant la comprovació de salut.")
    def get(self):
        """
        Realitza una comprovació de salut sense autenticació.

        Retorna una resposta 200 buida quan el servei és actiu.
        Codis d'estat:
        - 200: Servei disponible.
        - 500: Error no controlat en processar la comprovació.
        """
        try:
            self.logger.info("Health check requested", module="Health")
            return Response(status=200)
        except Exception as e:
            self.logger.error("Health check failed", module="Health", error=e)
            abort(500, message=f"S'ha produït un error inesperat en la comprovació de salut: {str(e)}")
