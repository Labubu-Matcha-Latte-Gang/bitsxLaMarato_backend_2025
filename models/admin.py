from db import db

class Admin(db.Model):
    __tablename__ = 'admins'

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