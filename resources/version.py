import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import current_app as app, Response

from helpers.debugger.logger import AbstractLogger

blp = Blueprint('version', __name__, description="Obtenir la versió actual de l'API.")

@blp.route('')
class Version(MethodView):
    """Exposa la versió actual de l'API definida a la configuració."""

    logger = AbstractLogger.get_instance()
    
    @blp.doc(
        security=[],
        summary="Versió de l'API",
        description="Retorna la cadena de versió configurada de l'API.",
    )
    @blp.response(200, description="Cadena de versió de l'API en text pla.")
    @blp.response(500, description="Error inesperat del servidor en obtenir la versió.")
    def get(self):
        """
        Retorna la versió actual de l'API.

        Llegeix `API_VERSION` de la configuració de Flask i l'envia en text pla.
        Codis d'estat:
        - 200: Cadena de versió retornada.
        - 500: No s'ha pogut recuperar o retornar el valor de la versió.
        """
        try:
            version: str = app.config.get('API_VERSION')
            self.logger.info("Version check requested", module="Version", metadata={"version": version})
            return Response(version, status=200, mimetype="text/plain")
        except Exception as e:
            self.logger.error("Version check failed", module="Version", error=e)
            abort(500, message=f"S'ha produït un error en obtenir la versió de l'API: {str(e)}")
