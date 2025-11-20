import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response

blp = Blueprint('health', __name__, description='Get the health status of the API.')

@blp.route('')
class Health(MethodView):
    """Returns the current health status of the API."""
    @blp.response(200, description="Current health status of the API.")
    @blp.response(500, description="Internal Server Error")
    def get(self):
        """Retrieve the current API health status."""
        try:
            return Response(status=200)
        except Exception as e:
            traceback.print_exc()
            abort(500, message=str(e))