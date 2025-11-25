from db import db
import bcrypt
from flask_jwt_extended import create_access_token
from datetime import timedelta

class User(db.Model):
    __tablename__ = 'users'
    
    email = db.Column(db.String(120), primary_key=True)
    password = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<User {self.name} {self.surname}, with email {self.email}>"
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password
        
        Args:
            password (str): The password to hash
            
        Returns:
            str: The hashed password
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """
        Check a password against the stored hash
        
        Args:
            password (str): The password to check

        Returns:
            bool: True if the password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
    
    def generate_jwt(self, expiration: timedelta | None = None) -> str:
        """
        Generate a JWT for the user
        Args:
            expiration (timedelta | None): The expiration time for the token. If None, defaults to 4 weeks.
        Returns:
            str: The generated JWT
        """
        expires = expiration or timedelta(weeks=4)
        return create_access_token(identity=self.email, expires_delta=expires)