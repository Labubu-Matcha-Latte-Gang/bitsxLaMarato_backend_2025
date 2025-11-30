import os
import tempfile
from flask import request, current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required
from openai import OpenAI

from db import db
from models.transcription import TranscriptionChunk
from helpers.debugger.logger import AbstractLogger
from schemas import TranscriptionChunkSchema, TranscriptionCompleteSchema, TranscriptionResponseSchema

blp = Blueprint('transcription', __name__, description="Operacions de transcripció d'àudio en temps real (Persistència en DB).")

def get_openai_client():
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        abort(500, message="La configuració del servidor no té la OPENAI_API_KEY definida.")
    return OpenAI(api_key=api_key)

@blp.route('/chunk')
class TranscriptionChunkResource(MethodView):
    """
    Gestió de la pujada de fragments d'àudio.
    """
    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.arguments(TranscriptionChunkSchema, location='form')
    @blp.doc(
        summary="Pujar fragment d'àudio",
        description="Rep un blob d'àudio, el transcriu i guarda el text a la base de dades PostgreSQL.",
        parameters=[
            {
                "name": "audio_blob",
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "El fitxer d'àudio del fragment (mp3, webm, etc.)"
            }
        ]
    )
    @blp.response(200, description="Fragment processat i guardat correctament.")
    @blp.response(400, description="Error en les dades d'entrada.")
    @blp.response(500, description="Error del servidor o d'OpenAI.")
    def post(self, form_data):
        session_id = form_data['session_id']
        chunk_index = form_data['chunk_index']
        
        if 'audio_blob' not in request.files:
            abort(400, message="Falta el fitxer 'audio_blob'.")
            
        audio_file = request.files['audio_blob']
        if audio_file.filename == '':
            abort(400, message="El fitxer no té nom.")

        temp_path = None
        try:
            self.logger.info(f"Processing DB chunk {chunk_index} for session {session_id}", module="Transcription")
            
            # 1. Guardar temporalment al disc per a Whisper
            suffix = os.path.splitext(audio_file.filename)[1] or ".webm"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
                audio_file.save(temp_audio.name)
                temp_path = temp_audio.name

            # 2. Transcriure amb OpenAI
            client = get_openai_client()
            with open(temp_path, "rb") as file_to_send:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=file_to_send,
                    language="ca" 
                )
                text_result = transcript.text

            # 3. Guardar a PostgreSQL
            new_chunk = TranscriptionChunk(
                session_id=session_id,
                chunk_index=chunk_index,
                text=text_result
            )
            db.session.add(new_chunk)
            db.session.commit()

            return {"status": "success", "partial_text": text_result}, 200

        except Exception as e:
            db.session.rollback() # Important fer rollback si falla
            self.logger.error("Error transcribing chunk", module="Transcription", error=e)
            abort(500, message=f"Error inesperat: {str(e)}")
        finally:
            # Esborrar fitxer temporal sempre
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)


@blp.route('/complete')
class TranscriptionCompleteResource(MethodView):
    """
    Finalització i assemblatge de la transcripció.
    """
    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.arguments(TranscriptionCompleteSchema, location='json')
    @blp.doc(
        summary="Finalitzar transcripció",
        description="Recupera tots els fragments de la DB, els ordena i retorna el text final. Opcionalment neteja les dades.",
    )
    @blp.response(200, schema=TranscriptionResponseSchema, description="Text complet retornat.")
    @blp.response(404, description="No s'han trobat fragments per a aquesta sessió.")
    def post(self, data):
        session_id = data['session_id']

        try:
            # 1. Recuperar fragments de PostgreSQL ordenats per índex
            chunks = TranscriptionChunk.query.filter_by(session_id=session_id)\
                        .order_by(TranscriptionChunk.chunk_index.asc())\
                        .all()

            if not chunks:
                abort(404, message="No s'ha trobat cap sessió activa amb aquest ID.")

            # 2. Unir text
            full_text = " ".join([chunk.text for chunk in chunks])
            
            # 3. Netejar la DB (Opcional: Si vols mantenir historial, comenta aquestes línies)
            #    És recomanable esborrar-los per no omplir la DB de dades temporals
            for chunk in chunks:
                db.session.delete(chunk)
            db.session.commit()
            
            self.logger.info(f"Session {session_id} completed via DB. Length: {len(full_text)} chars", module="Transcription")

            return {
                "status": "completed",
                "transcription": full_text
            }

        except Exception as e:
            db.session.rollback()
            self.logger.error("Error finalizing transcription", module="Transcription", error=e)
            abort(500, message=f"Error en finalitzar: {str(e)}")