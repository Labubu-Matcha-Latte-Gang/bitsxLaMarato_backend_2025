from models.patient import Patient
from models.doctor import Doctor
from models.admin import Admin

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

    patient: Patient | None = db.relationship('Patient', back_populates='user', uselist=False, cascade='all, delete-orphan')
    doctor: Doctor | None = db.relationship('Doctor', back_populates='user', uselist=False, cascade='all, delete-orphan')
    admin: Admin | None = db.relationship('Admin', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User {self.name} {self.surname}, email {self.email}>"
    
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
    
    def get_email(self) -> str:
        """
        Get the user's email
        Returns:
            str: The user's email
        """
        return self.email
    
    def get_name(self) -> str:
        """
        Get the user's name
        Returns:
            str: The user's name
        """
        return self.name
    
    def get_surname(self) -> str:
        """
        Get the user's surname
        Returns:
            str: The user's surname
        """
        return self.surname
    
    def set_password(self, new_password: str) -> None:
        """
        Set a new password for the user
        Args:
            new_password (str): The new password to set
        """
        self.password = self.hash_password(new_password)

    def get_role_instance(self) -> Patient | Doctor | Admin | None:
        """
        Get the role instance associated with the user
        Returns:
            Patient | Doctor | Admin | None: The associated role instance or None if no role is assigned
        """
        if self.patient:
            return self.patient
        if self.doctor:
            return self.doctor
        if self.admin:
            return self.admin
        return None
    
    def set_email(self, new_email: str) -> None:
        """
        Set a new email for the user
        Args:
            new_email (str): The new email to set
        """
        self.email = new_email

        if self.patient:
            self.patient.email = new_email
        if self.doctor:
            self.doctor.email = new_email
        if self.admin:
            self.admin.email = new_email

    def set_name(self, new_name: str) -> None:
        """
        Set a new name for the user
        Args:
            new_name (str): The new name to set
        """
        self.name = new_name

    def set_surname(self, new_surname: str) -> None:
        """
        Set a new surname for the user
        Args:
            new_surname (str): The new surname to set
        """
        self.surname = new_surname

    def to_dict(self) -> dict:
        """
        Convert the user to a dictionary representation
        Returns:
            dict: The dictionary representation of the user
        """
        role = self.get_role_instance()
        if role is None:
            return {
                "email": self.email,
                "name": self.name,
                "surname": self.surname
            }
        return {
            "email": self.email,
            "name": self.name,
            "surname": self.surname,
            "role": role.to_dict()
        }