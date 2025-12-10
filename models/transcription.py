from db import db
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB 

class TranscriptionChunk(db.Model):
    __tablename__ = 'transcription_chunks'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    analysis = db.Column(JSONB, nullable=True)

    created_at = db.Column(db.DateTime, server_default=func.now())

    # Constraint de unicidad para evitar chunks duplicados
    __table_args__ = (
        db.UniqueConstraint('session_id', 'chunk_index', name='uq_transcription_chunks_session_chunk'),
        db.Index('ix_transcription_chunks_session_index', 'session_id', 'chunk_index'),
    )