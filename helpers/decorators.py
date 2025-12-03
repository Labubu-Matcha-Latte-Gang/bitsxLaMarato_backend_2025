from functools import wraps
from typing import Sequence
from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_smorest import abort
from helpers.enums.user_role import UserRole
from helpers.exceptions.user_exceptions import UserNotFoundException
from application.container import ServiceFactory

def roles_required(roles: Sequence[UserRole]):
    """
    Decorator that requires the user to have one of the specified roles.
    Args:
        roles (Sequence[UserRole]): The roles required to access the endpoint
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            email: str = get_jwt_identity()

            user_service = ServiceFactory().build_user_service()
            try:
                user = user_service.get_user(email)
            except UserNotFoundException:
                abort(401, message="Token d'autenticació no vàlid.")
            except Exception as exc:
                abort(409, message=str(exc))

            role = user.role
            if role not in roles:
                abort(403, message="No tens el rol necessari per accedir a aquest recurs.")

            g.current_user = user
            g.current_role_instance = user

            return f(*args, **kwargs)
        return decorated_function
    return decorator
