from db import db
from helpers.enums.user_role import UserRole
from models.interfaces import IUserRole

class Admin(db.Model, IUserRole):
    __tablename__ = 'admins'
    __allow_unmapped__ = True

    email = db.Column(db.String(120), db.ForeignKey('users.email', onupdate='CASCADE'), primary_key=True)
    user = db.relationship('User', back_populates='admin', uselist=False)

    def get_user(self):
        """
        Get the associated User object
        Returns:
            User: The associated User object
        """
        return self.user
    
    def get_email(self) -> str:
        """
        Get the admin's email
        Returns:
            str: The admin's email
        """
        return self.email
    
    def set_email(self, new_email: str) -> None:
        """
        Set a new email for the admin
        Args:
            new_email (str): The new email to set
        """
        user = self.get_user()
        user.set_email(new_email)

    def to_dict(self) -> dict:
        """
        Convert the Admin object to a dictionary
        Returns:
            dict: A dictionary representation of the Admin object
        """
        return {}
    
    def get_role(self) -> UserRole:
        """
        Get the role of this user
        Returns:
            UserRole: The role of this user
        """
        return UserRole.ADMIN

    def doctor_of_this_patient(self, patient) -> bool:
        """
        Admins are allowed to access any patient.
        """
        return True
    
    def remove_all_associations(self) -> None:
        """
        Remove all associations with other entities
        """
        return  # No associations to remove for Admin at this time
    
    def set_properties(self, data: dict) -> None:
        """
        Set multiple properties of the admin from a dictionary
        Args:
            data (dict): A dictionary containing the properties to set
        """
        return  # No additional properties to set for Admin at this time
