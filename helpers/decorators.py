from functools import wraps
from typing import Sequence
from flask_jwt_extended import get_jwt_identity
from flask_smorest import abort
from helpers.enums.user_role import UserRole
from models.user import User

def roles_required(roles: Sequence[UserRole]):
    """
    Decorator that requires the user to have one of the specified roles.
    Should be used together with @jwt_required().
    Args:
        roles (Sequence[UserRole]): The roles required to access the endpoint
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            email:str = get_jwt_identity()
            
            user:User|None = User.query.get(email)
            if not user:
                abort(401, message="Invalid authentication token.")

            role_instance = user.get_role_instance()
            if role_instance is None:
                abort(403, message="You do not have the required role to access this resource.")
            role = role_instance.get_role()
            if role not in roles:
                abort(403, message="You do not have the required role to access this resource.")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator