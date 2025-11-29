from db import db
from sqlalchemy.sql import func

class TranscriptionChunk(db.Model):
    __tablename__ = 'transcription_chunks'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, index=True) # Indexado para busquedas ràpides
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())