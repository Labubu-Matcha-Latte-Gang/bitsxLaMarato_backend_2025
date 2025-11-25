from db import db

from models.user import User

class Doctor(db.Model):
    __tablename__ = 'doctors'
    
    email = db.Column(db.String(120), db.ForeignKey('users.email'), primary_key=True)
    __user: User = db.relationship('User', backref=db.backref('patient', uselist=False))
    patients = db.relationship('Patient', backref='doctor', lazy=True)
    
    def get_user(self) -> User:
        """
        Get the associated User object
        Returns:
            User: The associated User object
        """
        return self.__user