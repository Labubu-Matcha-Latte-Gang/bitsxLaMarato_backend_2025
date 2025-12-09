from datetime import timedelta
from typing import Optional

from flask_jwt_extended import create_access_token, decode_token


class TokenService:
    """
    JWT token generation service.
    """

    def generate(self, identity: str, expiration: Optional[timedelta] = None) -> str:
        return create_access_token(identity=identity, expires_delta=expiration or timedelta(weeks=4))

    def parse(self, token: str) -> str:
        decoded_data = decode_token(token)
        return decoded_data["sub"]