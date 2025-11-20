import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import current_app as app, Response

blp = Blueprint('version', __name__, description='Get the current version of the API.')

@blp.route('')
class Version(MethodView):
    """Returns the current version of the API."""

    @blp.response(200, description="Current version of the API.")
    @blp.response(500, description="Internal Server Error")
    def get(self):
        """Retrieve the current API version."""
        try:
            version: str = app.config.get('API_VERSION')
            return Response(version, status=200, mimetype="text/plain")
        except Exception as e:
            traceback.print_exc()
            abort(500, message=str(e))