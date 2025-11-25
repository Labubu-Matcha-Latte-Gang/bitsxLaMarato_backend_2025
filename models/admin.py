from db import db

from models.user import User

class Admin(db.Model):
    __tablename__ = 'admins'
    
    email = db.Column(db.String(120), db.ForeignKey('users.email'), primary_key=True)
    __user: User = db.relationship('User', backref=db.backref('patient', uselist=False))
    
    def get_user(self) -> User:
        """
        Get the associated User object
        Returns:
            User: The associated User object
        """
        return self.__user