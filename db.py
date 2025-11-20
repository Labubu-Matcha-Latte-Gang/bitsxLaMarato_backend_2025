"""
Database module for the Flask application.
This module initializes the SQLAlchemy database instance and connects it to the Flask application.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_db(app:Flask) -> SQLAlchemy:
    """
    Connects the SQLAlchemy database instance to the Flask application.
    Args:
        app (Flask): The Flask application instance.
    Returns:
        SQLAlchemy: The SQLAlchemy database instance connected to the Flask application.
    """
    db.init_app(app)
    return db