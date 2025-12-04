import os
import tempfile
import json
from flask import request, current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required
from openai import AzureOpenAI
from sqlalchemy.exc import IntegrityError

from db import db
from models.transcription import TranscriptionChunk
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.integrity_exceptions import DataIntegrityException
from helpers.analysis_engine import analyze_audio_signal, analyze_linguistics, analyze_executive_functions
from infrastructure.sqlalchemy.unit_of_work import map_integrity_error
from schemas import TranscriptionChunkSchema, TranscriptionCompleteSchema, TranscriptionResponseSchema

blp = Blueprint('transcription', __name__, description="Operacions de transcripció d'àudio en temps real (Persistència en DB).")

def get_azure_client():
    api_key = current_app.config.get("AZURE_OPENAI_API_KEY")
    endpoint = current_app.config.get("AZURE_OPENAI_ENDPOINT")
    api_version = current_app.config.get("AZURE_OPENAI_API_VERSION")

    if not api_key or not endpoint:
        abort(500, message="Falten credencials d'Azure OpenAI a la configuració.")

    return AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )

@blp.route('/chunk')
class TranscriptionChunkResource(MethodView):
    """
    Gestió de la pujada de fragments d'àudio amb anàlisi cognitiu.
    """
    logger = AbstractLogger.get_instance()

    @jwt_required()
    @blp.arguments(TranscriptionChunkSchema, location='form')
    @blp.doc(
        summary="Pujar fragment d'àudio",
        description="Rep un blob d'àudio, l'analitza (física i lingüísticament), el transcriu i guarda el resultat.",
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
            
            # 1. Guardar temporalment al disc
            suffix = os.path.splitext(audio_file.filename)[1] or ".webm"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
                audio_file.save(temp_audio.name)
                temp_path = temp_audio.name

            # ---------------------------------------------------------
            # 2. ANÀLISI DE SENYAL (Abans d'enviar a OpenAI)
            # ---------------------------------------------------------
            # Això ens dona mètriques de "Velocitat de Processament" reals (pauses, fonació)
            acoustic_metrics = analyze_audio_signal(temp_path)

            # ---------------------------------------------------------
            # 3. TRANSCRIPCIÓ (Azure OpenAI)
            # ---------------------------------------------------------
            client = get_azure_client()
            deployment_name = current_app.config.get("AZURE_OPENAI_DEPLOYMENT_NAME")
            
            with open(temp_path, "rb") as file_to_send:
                transcript = client.audio.transcriptions.create(
                    model=deployment_name,
                    file=file_to_send,
                    language="ca",
                    response_format="verbose_json"
                )
                text_result = transcript.text
                segments = transcript.segments

            # ---------------------------------------------------------
            # 4. ANÀLISI LINGÜÍSTIC (spaCy)
            # ---------------------------------------------------------
            # Això ens dona mètriques d'"Accés Lèxic" (Anomia, riquesa verbal)
            linguistic_metrics = analyze_linguistics(text_result)

            # ---------------------------------------------------------
            # 5. UNIFICAR MÈTRIQUES
            # ---------------------------------------------------------
            combined_metrics = {
                **acoustic_metrics,   # duration, phonation_ratio, pause_time...
                **linguistic_metrics, # p_n_ratio, idea_density, noun_count...
                "raw_latency": segments[0].start if segments else 0 # Access attribute, not dictionary
            }

            # 6. Guardar a PostgreSQL
            new_chunk = TranscriptionChunk(
                session_id=session_id,
                chunk_index=chunk_index,
                text=text_result,
                analysis=combined_metrics
            )
            db.session.add(new_chunk)
            db.session.commit()

            # Retornem les dades perquè el Frontend pugui pintar gràfiques en temps real
            return {
                "status": "success", 
                "partial_text": text_result,
                "analysis": combined_metrics 
            }, 200
        
        except IntegrityError as e:
            db.session.rollback()
            mapped = map_integrity_error(e)
            self.logger.error("Integrity violation transcribing chunk", module="Transcription", error=mapped)
            abort(422, message=str(mapped))
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error transcribing chunk", module="Transcription", error=e)
            abort(500, message=f"S'ha produït un error inesperat: {str(e)}")
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
        description="Recupera tots els fragments de la DB, els ordena i retorna el text final amb anàlisi complet.",
    )
    @blp.response(200, schema=TranscriptionResponseSchema, description="Text complet retornat.")
    @blp.response(404, description="No s'han trobat fragments per a aquesta sessió.")
    def post(self, data):
        session_id = data['session_id']

        try:
            # 1. Recuperar fragments
            chunks = TranscriptionChunk.query.filter_by(session_id=session_id)\
                        .order_by(TranscriptionChunk.chunk_index.asc())\
                        .all()

            if not chunks:
                abort(404, message="No s'ha trobat cap sessió activa amb aquest ID.")

            # 2. Unir text
            full_text = " ".join([chunk.text for chunk in chunks])
            
            # ---------------------------------------------------------
            # 3. ANÀLISI INTEGRAL (Text Complet)
            # ---------------------------------------------------------
            # A. Funcions Executives (Planificació, Coherència)
            executive_metrics = analyze_executive_functions(full_text)
            
            # B. Lingüística (Anomia, Densitat) -
            linguistic_metrics = analyze_linguistics(full_text)

            # C. Recuperar mètriques físiques mitjanes (Opcional, si volem mantenir dades de veu)
            # Com que no tenim l'àudio, podríem fer la mitjana dels chunks si ho guardéssim a la DB.
            # Per ara, retornem la combinació de Exec + Ling.
            
            final_metrics = {
                **executive_metrics,
                **linguistic_metrics
            }

            # 4. Netejar la DB
            for chunk in chunks:
                db.session.delete(chunk)
            db.session.commit()
            
            self.logger.info(f"Session {session_id} completed. Metrics: {final_metrics}", module="Transcription")

            return {
                "status": "completed",
                "transcription": full_text,
                "analysis": final_metrics 
            }, 200

        except IntegrityError as e:
            db.session.rollback()
            mapped = map_integrity_error(e)
            self.logger.error("Integrity violation finalizing transcription", module="Transcription", error=mapped)
            abort(422, message=str(mapped))
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error finalizing transcription", module="Transcription", error=e)
            abort(500, message=f"S'ha produït un error en finalitzar: {str(e)}")