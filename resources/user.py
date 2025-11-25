from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response

from helpers.debugger.logger import AbstractLogger
from schemas import UserRegisterSchema

blp = Blueprint('user', __name__, description='User related operations')

@blp.route('')
class User(MethodView):
    """
    User Resource
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(UserRegisterSchema, location='json')
    @blp.response(201, description="User successfully registered")
    @blp.response(400, description="Bad Request")
    @blp.response(500, description="Internal Server Error")
    def post(self, data: dict) -> Response:
        """Register a new user"""
        try:
            self.logger.info("Start registering a user", module="User", metadata=data)
            return Response(status=200)
        except Exception as e:
            self.logger.error("User register failed", module="User", error=e)
            abort(500, message=str(e))