import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import current_app as app, Response

from helpers.debugger.logger import AbstractLogger

blp = Blueprint('version', __name__, description='Get the current version of the API.')

@blp.route('')
class Version(MethodView):
    """Expose the current API version from configuration."""

    logger = AbstractLogger.get_instance()
    
    @blp.doc(
        security=[],
        summary="API version",
        description="Returns the configured API version string.",
    )
    @blp.response(200, description="Plain-text API version string.")
    @blp.response(500, description="Unexpected server error while retrieving the version.")
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
            abort(500, message=str(e))
