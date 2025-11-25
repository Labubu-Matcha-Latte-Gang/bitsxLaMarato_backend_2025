from db import db

from models.user import User

class Patient(db.Model):
    __tablename__ = 'patients'
    
    email = db.Column(db.String(120), db.ForeignKey('users.email'), primary_key=True)
    ailments = db.Column(db.String(1024), nullable=True)
    __user: User = db.relationship('User', backref=db.backref('patient', uselist=False))
    
    def get_user(self) -> User:
        """
        Get the associated User object
        Returns:
            User: The associated User object
        """
        return self.__user