from datetime import timedelta
from typing import Optional

from flask_jwt_extended import create_access_token, decode_token
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import ExpiredSignatureError, InvalidTokenError

from helpers.exceptions.user_exceptions import ExpiredTokenException, InvalidTokenException


class TokenService:
    """
    JWT token generation service.
    """

    def generate(self, identity: str, expiration: Optional[timedelta] = None) -> str:
        return create_access_token(identity=identity, expires_delta=expiration or timedelta(weeks=4))

    def parse(self, token: str) -> str:
        try:
            decoded_data = decode_token(token)
            return decoded_data["sub"]
        except ExpiredSignatureError as exc:
            raise ExpiredTokenException("El token d'accés ha caducat.") from exc
        except (JWTExtendedException, InvalidTokenError, KeyError) as exc:
            raise InvalidTokenException("Token d'accés invàlid.") from exc
