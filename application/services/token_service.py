from datetime import timedelta
from typing import Optional

from flask_jwt_extended import create_access_token


class TokenService:
    """
    JWT token generation service.
    """

    def generate(self, identity: str, expiration: Optional[timedelta] = None) -> str:
        return create_access_token(identity=identity, expires_delta=expiration or timedelta(weeks=4))
