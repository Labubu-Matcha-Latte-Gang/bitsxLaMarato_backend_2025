import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import current_app as app, Response

from helpers.debugger.logger import AbstractLogger

blp = Blueprint('version', __name__, description="Obtenir la versió actual de l'API.")

@blp.route('')
class Version(MethodView):
    """Expose the current API version from configuration."""

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
        Return the current API version.

        Reads `API_VERSION` from the Flask configuration and sends it as plain text.
        Status codes:
        - 200: Version string returned.
        - 500: Failed to retrieve or return the version value.
        """
        try:
            version: str = app.config.get('API_VERSION')
            self.logger.info("Version check requested", module="Version", metadata={"version": version})
            return Response(version, status=200, mimetype="text/plain")
        except Exception as e:
            self.logger.error("Version check failed", module="Version", error=e)
            abort(500, message=f"S'ha produït un error en obtenir la versió de l'API: {str(e)}")
