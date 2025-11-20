import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import current_app as app, Response

from helpers.debugger.logger import AbstractLogger

blp = Blueprint('version', __name__, description='Get the current version of the API.')

@blp.route('')
class Version(MethodView):
    """Returns the current version of the API."""

    logger = AbstractLogger.get_instance()
    
    @blp.response(200, description="Current version of the API.")
    @blp.response(500, description="Internal Server Error")
    def get(self):
        """Retrieve the current API version."""
        try:
            version: str = app.config.get('API_VERSION')
            self.logger.info("Version check requested", module="Version", metadata={"version": version})
            return Response(version, status=200, mimetype="text/plain")
        except Exception as e:
            self.logger.error("Version check failed", module="Version", error=e)
            abort(500, message=str(e))