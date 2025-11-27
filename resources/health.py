import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response

from helpers.debugger.logger import AbstractLogger

blp = Blueprint('health', __name__, description='Get the health status of the API.')

@blp.route('')
class Health(MethodView):
    """Returns the current health status of the API."""

    logger = AbstractLogger.get_instance()

    @blp.doc(security=[])
    @blp.response(200, description="Current health status of the API.")
    @blp.response(500, description="Internal Server Error")
    def get(self):
        """Retrieve the current API health status."""
        try:
            self.logger.info("Health check requested", module="Health")
            return Response(status=200)
        except Exception as e:
            self.logger.error("Health check failed", module="Health", error=e)
            abort(500, message=str(e))
