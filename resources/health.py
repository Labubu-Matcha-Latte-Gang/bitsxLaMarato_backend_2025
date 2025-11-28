import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response

from helpers.debugger.logger import AbstractLogger

blp = Blueprint('health', __name__, description='Get the health status of the API.')

@blp.route('')
class Health(MethodView):
    """Lightweight liveness probe for the API."""

    logger = AbstractLogger.get_instance()

    @blp.doc(
        security=[],
        summary="Health check",
        description="Returns 200 when the service is reachable.",
    )
    @blp.response(200, description="Service is reachable.")
    @blp.response(500, description="Unexpected server error while performing the health check.")
    def get(self):
        """
        Perform an unauthenticated health probe.

        Returns an empty 200 response when the service is up.
        Status codes:
        - 200: Service reachable.
        - 500: Unhandled error when processing the probe.
        """
        try:
            self.logger.info("Health check requested", module="Health")
            return Response(status=200)
        except Exception as e:
            self.logger.error("Health check failed", module="Health", error=e)
            abort(500, message=str(e))
