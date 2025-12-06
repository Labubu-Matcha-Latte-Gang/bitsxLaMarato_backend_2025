import os
import subprocess
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

SESSION_HEADERS = {}

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
        converted_wav_path = None
        fixed_input_path = None
        self.logger.info(f"Processing chunk {chunk_index} for session {session_id}", module="Transcription")
        try:
            suffix = os.path.splitext(audio_file.filename)[1] or ".webm"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
                audio_file.save(temp_audio.name)
                temp_path = temp_audio.name

            # Si el formato no es WAV, prepararlo para conversión (reparar WebM si hace falta)
            if suffix != ".wav":
                # Reparar encabezado si no es el primer chunk y es WebM
                if suffix == ".webm":
                    with open(temp_path, "rb") as f:
                        full_data = f.read()

                    if int(chunk_index) == 0:
                        cluster_start = full_data.find(b'\x1f\x43\xb6\x75')
                        header = full_data if cluster_start == -1 else full_data[:cluster_start]
                        SESSION_HEADERS[session_id] = header
                        final_data = full_data
                    else:
                        header = SESSION_HEADERS.get(session_id)
                        if not header:
                            abort(400, message="No s'ha trobat capçalera per aquesta sessió.")
                        final_data = header + full_data

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as fixed_file:
                        fixed_file.write(final_data)
                        fixed_input_path = fixed_file.name
                else:
                    fixed_input_path = temp_path  # otro formato no WebM: usar tal cual

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as converted:
                    converted_wav_path = converted.name

                subprocess.run([
                    "ffmpeg", "-y", "-i", fixed_input_path,
                    "-ac", "1", "-ar", "16000",
                    converted_wav_path
                ], check=True)
            else:
                converted_wav_path = temp_path

            # Análisis acústico (físico)
            acoustic_metrics = analyze_audio_signal(converted_wav_path)

            # Transcripción via OpenAI
            client = get_azure_client()
            deployment_name = current_app.config.get("AZURE_OPENAI_DEPLOYMENT_NAME")

            with open(converted_wav_path, "rb") as file_to_send:
                transcript = client.audio.transcriptions.create(
                    model=deployment_name,
                    file=file_to_send,
                    language="ca",
                    response_format="verbose_json"
                )

            text_result = transcript.text
            segments = transcript.segments

            # Análisis lingüístico
            linguistic_metrics = analyze_linguistics(text_result)

            combined_metrics = {
                **acoustic_metrics,
                **linguistic_metrics,
                "raw_latency": segments[0].start if segments else 0
            }

            new_chunk = TranscriptionChunk(
                session_id=session_id,
                chunk_index=chunk_index,
                text=text_result,
                analysis=combined_metrics
            )
            db.session.add(new_chunk)
            db.session.commit()

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
            for path in [temp_path, fixed_input_path, converted_wav_path]:
                if path and os.path.exists(path):
                    os.remove(path)

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