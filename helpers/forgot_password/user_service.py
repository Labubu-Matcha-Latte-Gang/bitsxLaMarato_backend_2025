import secrets
import string
from db import db
from globals import RESET_CODE_VALIDITY_MINUTES
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.user_exceptions import InvalidResetCodeException, UserNotFoundException
from models.user import User
from models.associations import UserCodeAssociation
from datetime import datetime, timedelta, timezone

class UserService:
    __instance: 'UserService' = None
    logger = AbstractLogger.get_instance()

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> 'UserService':
        if cls.__instance is None:
            cls.__instance = UserService()
        return cls.__instance
    
    @staticmethod
    def generate_reset_code() -> str:
        """
        Generate a unique reset code for password recovery.
        Returns:
            str: A reset code consisting of 8 alphanumeric characters.
        """
        alphabet = string.ascii_letters + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        return code
    
    def user_forgot_password(self, email: str) -> str:
        """
        Handle the forgot password process for a user.
        Args:
            email (str): The email address of the user who forgot their password.
        Returns:
            str: The generated reset code.
        """
        user: User | None = User.query.get(email)
        if user is None:
            raise UserNotFoundException(f"User with email {email} not found.")
    
        reset_code = self.generate_reset_code()
        hashed_code = User.hash_password(reset_code)
        try:
            existing_association: UserCodeAssociation | None = UserCodeAssociation.query.get(email)
            if existing_association is not None:
                db.session.delete(existing_association)

            expiration = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_VALIDITY_MINUTES)
            user_code_association = UserCodeAssociation(user_email=email, code=hashed_code, expiration=expiration)
            db.session.add(user_code_association)
            db.session.commit()
            return reset_code
        except Exception as e:
            db.session.rollback()
            self.logger.error(message=f"Error saving reset code for user {email}", metadata={"email": email}, module=__name__, error=e)
            raise e
        
    def user_reset_password(self, email: str, reset_code: str, new_password: str) -> None:
        """
        Reset the user's password using the provided reset code.
        Args:
            email (str): The email address of the user.
            reset_code (str): The reset code provided by the user.
            new_password (str): The new password to set.
        Raises:
            UserNotFoundException: If the user with the given email is not found.
            InvalidResetCodeException: If the reset code is invalid or expired.
        """
        user: User | None = User.query.get(email)
        if user is None:
            raise UserNotFoundException(f"User with email {email} not found.")
        
        association: UserCodeAssociation | None = UserCodeAssociation.query.get(email)

        if association is None:
            raise InvalidResetCodeException("The provided reset code is invalid or has expired.")
        
        if association.is_expired(datetime.now(timezone.utc)):
            try:
                db.session.delete(association)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                self.logger.error(message=f"Error deleting expired reset code for user {email}", metadata={"email": email}, module=__name__, error=e)
                raise e
            raise InvalidResetCodeException("The provided reset code is invalid or has expired.")
        
        if not association.check_code(reset_code):
            raise InvalidResetCodeException("The provided reset code is invalid or has expired.")

        try:
            user.set_password(new_password)
            db.session.delete(association)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            self.logger.error(message=f"Error resetting password for user {email}", metadata={"email": email}, module=__name__, error=e)
            raise e