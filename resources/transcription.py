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

# Add error handler for request parsing issues
@blp.errorhandler(400)
def handle_bad_request(error):
    """Handle flask-smorest parsing errors that manifest as 400 errors."""
    logger = AbstractLogger.get_instance()
    error_description = getattr(error, 'description', str(error))
    
    if "could not understand" in error_description or "browser" in error_description:
        logger.error(f"Request parsing error caught: {error_description}", module="Transcription")
        return {
            "code": 400,
            "message": "Format de dades incorrecte. Verificar estructura multipart/form-data i codificació dels fitxers.",
            "status": "Bad Request"
        }, 400
    
    # For other 400 errors, return as-is
    return {
        "code": 400,
        "message": error_description,
        "status": "Bad Request"
    }, 400

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

    def _detect_webm_format(self, file_data, chunk_index):
        """
        Detect if WebM data is a complete file or a fragment.
        Frontend MediaRecorder can send complete files or streaming fragments.
        """
        if len(file_data) < 10:
            return 'invalid'
            
        # Check for EBML header (complete WebM file)
        if file_data.startswith(b'\x1A\x45\xDF\xA3'):
            return 'complete_webm'
            
        # Check for WebM segment data (partial chunk)
        if b'webm' in file_data[:100].lower() or chunk_index == 0:
            return 'webm_header'
            
        # Check if it's likely a media fragment (no headers)
        if len(file_data) > 1000 and chunk_index > 0:
            return 'webm_fragment'
            
        return 'unknown'

    def _handle_webm_chunk(self, file_data, session_id, chunk_index):
        """
        Handle different types of WebM chunks from frontend MediaRecorder.
        """
        format_type = self._detect_webm_format(file_data, chunk_index)
        self.logger.info(f"WebM format detected: {format_type} for chunk {chunk_index}", module="Transcription")
        
        if format_type == 'complete_webm':
            # Complete WebM file - process normally
            return file_data
        elif format_type == 'webm_header' and chunk_index == 0:
            # First chunk with headers - store for later use
            self._webm_headers = file_data[:1024]  # Store first 1KB as headers
            return file_data
        elif format_type == 'webm_fragment' and hasattr(self, '_webm_headers'):
            # Fragment without headers - try to combine with stored headers
            self.logger.info(f"Attempting to repair WebM fragment using stored headers", module="Transcription")
            return self._webm_headers + file_data
        else:
            # Unknown format or can't repair - return as-is and let FFmpeg handle it
            self.logger.warning(f"Cannot identify WebM format for chunk {chunk_index}, size: {len(file_data)}", module="Transcription")
            return file_data

    def _repair_webm_and_convert(self, input_path, output_path, session_id, chunk_index):
        """
        Intentar reparar chunks WebM usando headers almacenados en el primer chunk.
        Fallback mejorado para cuando la conversión directa falla.
        """
        try:
            with open(input_path, "rb") as f:
                full_data = f.read()

            # Validar que tenemos datos
            if len(full_data) < 100:  # WebM muy pequeño, probablemente corrupto
                raise ValueError(f"Audio chunk too small ({len(full_data)} bytes), likely corrupted")

            if int(chunk_index) == 0:
                # Primer chunk: extraer header y guardar para posible uso futuro
                cluster_start = full_data.find(b'\x1f\x43\xb6\x75')
                header = full_data if cluster_start == -1 else full_data[:cluster_start]
                
                # Guardar header en el análisis del primer chunk (se hará después de guardarlo)
                self._temp_header_data = header
                final_data = full_data
            else:
                # Chunks posteriores: buscar header del primer chunk
                first_chunk = TranscriptionChunk.query.filter_by(
                    session_id=session_id, chunk_index=0
                ).first()
                
                header = None
                if first_chunk and first_chunk.analysis and 'webm_header' in first_chunk.analysis:
                    # El header está guardado como base64 en el análisis del primer chunk
                    import base64
                    try:
                        header = base64.b64decode(first_chunk.analysis['webm_header'])
                    except:
                        header = None
                
                if header:
                    final_data = header + full_data
                    self.logger.info(f"Using stored header for chunk {chunk_index}, total size: {len(final_data)} bytes", module="Transcription")
                else:
                    # Si no hay header disponible, intentar sin reparación
                    self.logger.warning(f"No header found for session {session_id}, using raw chunk", module="Transcription")
                    final_data = full_data

            # Crear archivo WebM temporal reparado
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as fixed_file:
                fixed_file.write(final_data)
                fixed_input_path = fixed_file.name

            try:
                # Convertir a WAV con opciones más robustas
                cmd = [
                    "ffmpeg", "-y", 
                    "-f", "webm",  # Forzar formato de entrada
                    "-i", fixed_input_path,
                    "-ac", "1", "-ar", "16000",
                    "-f", "wav",  # Forzar formato de salida
                    "-acodec", "pcm_s16le",  # Codec específico
                    output_path
                ]
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                self.logger.info(f"WebM repair successful for chunk {chunk_index}", module="Transcription")
                
            except subprocess.CalledProcessError as e:
                error_details = e.stderr[:300] if e.stderr else "No error details"
                self.logger.error(f"WebM repair FFmpeg failed for chunk {chunk_index}: {error_details}", module="Transcription")
                raise
        
        except Exception as e:
            self.logger.error(f"WebM repair process failed for chunk {chunk_index}: {str(e)}", module="Transcription")
            raise
        
        finally:
            # Limpiar archivo temporal
            if 'fixed_input_path' in locals() and os.path.exists(fixed_input_path):
                try:
                    os.remove(fixed_input_path)
                except Exception as cleanup_error:
                    self.logger.warning(f"Could not cleanup WebM temp file: {cleanup_error}", module="Transcription")

    @jwt_required()
    @blp.doc(
        summary="Pujar fragment d'àudio",
        description="Rep un blob d'àudio, l'analitza (física i lingüísticament), el transcriu i guarda el resultat.",
        parameters=[
            {
                "name": "session_id",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Identificador únic de la sessió d'enregistrament."
            },
            {
                "name": "chunk_index",
                "in": "formData", 
                "type": "integer",
                "required": True,
                "description": "Índex seqüencial del fragment."
            },
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
    def post(self):
        # Parse form data manually with enhanced error handling
        try:
            # Log request details for debugging
            self.logger.info(f"Request content type: {request.content_type}, length: {request.content_length}", module="Transcription")
            
            session_id = request.form.get('session_id')
            chunk_index_str = request.form.get('chunk_index')
            
            self.logger.info(f"Parsed form data - session_id: '{session_id}', chunk_index: '{chunk_index_str}'", module="Transcription")
            
        except Exception as form_error:
            error_msg = str(form_error)
            self.logger.error(f"Form parsing error: {error_msg}", module="Transcription")
            
            if "could not understand" in error_msg.lower() or "browser" in error_msg.lower():
                abort(400, message="Error de format del frontend. Les dades WebM poden estar corruptes o mal formateades.")
            else:
                abort(400, message=f"Error processant formulari: {error_msg}")
        
        if not session_id:
            abort(400, message="Falta el paràmetre 'session_id'.")
        if not chunk_index_str:
            abort(400, message="Falta el paràmetre 'chunk_index'.")
            
        try:
            chunk_index = int(chunk_index_str)
        except (ValueError, TypeError):
            abort(400, message="El 'chunk_index' ha de ser un número enter.")

        if 'audio_blob' not in request.files:
            abort(400, message="Falta el fitxer 'audio_blob'.")

        audio_file = request.files['audio_blob']
        if audio_file.filename == '':
            abort(400, message="El fitxer no té nom.")

        # Enhanced file validation with WebM chunk handling
        try:
            # Read file data to validate
            initial_position = audio_file.tell()
            file_data = audio_file.read()
            audio_file.seek(initial_position)  # Reset position
            
            self.logger.info(f"File details - name: '{audio_file.filename}', size: {len(file_data)} bytes, content_type: '{audio_file.content_type}'", module="Transcription")
            
            # Special handling for WebM files from frontend MediaRecorder
            if audio_file.filename.endswith('.webm'):
                # Process WebM chunk using specialized handler
                processed_data = self._handle_webm_chunk(file_data, session_id, chunk_index)
                
                if len(processed_data) < 100:
                    self.logger.error(f"WebM chunk {chunk_index} too small after processing: {len(processed_data)} bytes", module="Transcription")
                    abort(400, message=f"Chunk WebM {chunk_index} massa petit després del processament. Dades corruptes del frontend.")
                
                # Update the file data with processed version
                audio_file.seek(0)
                audio_file.truncate()
                audio_file.write(processed_data)
                audio_file.seek(0)
                
                self.logger.info(f"WebM chunk {chunk_index} processed successfully, final size: {len(processed_data)} bytes", module="Transcription")
            
        except Exception as file_error:
            self.logger.error(f"File validation/processing error: {file_error}", module="Transcription")
            abort(400, message="Error processant fitxer WebM del frontend. Possible problema amb MediaRecorder.")

        temp_path = None
        converted_wav_path = None
        self.logger.info(f"Processing chunk {chunk_index} for session {session_id}", module="Transcription")
        try:
            suffix = os.path.splitext(audio_file.filename)[1] or ".webm"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
                audio_file.save(temp_audio.name)
                temp_path = temp_audio.name

            # Si el formato no es WAV, prepararlo para conversión
            if suffix != ".wav":
                # Para WebM y otros formatos, intentar conversión directa primero
                # Si falla, usar el fallback mejorado
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as converted:
                    converted_wav_path = converted.name

                # Validar tamaño del archivo de entrada
                file_size = os.path.getsize(temp_path)
                if file_size < 100:  # Muy pequeño, probablemente corrupto
                    self.logger.warning(f"Audio file very small ({file_size} bytes), may be corrupted", module="Transcription")
                    abort(400, message="El fitxer d'àudio és massa petit o està corrupte.")

                try:
                    # Intentar conversión directa con FFmpeg (más robusta)
                    cmd = [
                        "ffmpeg", "-y", 
                        "-i", temp_path,
                        "-ac", "1", "-ar", "16000",
                        "-f", "wav",  # Forzar formato WAV
                        "-acodec", "pcm_s16le",  # Codec específico
                        converted_wav_path
                    ]
                    
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    self.logger.info(f"Direct audio conversion successful for chunk {chunk_index}", module="Transcription")
                    
                except subprocess.CalledProcessError as e:
                    # Si falla la conversión directa, intentar con headers WebM (fallback)
                    if suffix == ".webm":
                        error_details = e.stderr[:200] if e.stderr else "No error details"
                        self.logger.warning(f"Direct conversion failed, trying WebM header repair for chunk {chunk_index}: {error_details}", module="Transcription")
                        try:
                            self._repair_webm_and_convert(temp_path, converted_wav_path, session_id, chunk_index)
                        except Exception as repair_error:
                            self.logger.error(f"WebM repair also failed: {repair_error}", module="Transcription")
                            abort(400, message="No s'ha pogut processar el fitxer WebM. Potser està corrupte o és invàlid.")
                    else:
                        # Para otros formatos, lanzar error más específico
                        error_msg = e.stderr[:300] if e.stderr else str(e)
                        self.logger.error(f"Audio conversion failed for format {suffix}: {error_msg}", module="Transcription")
                        abort(400, message=f"No s'ha pogut convertir l'àudio {suffix}. Format no suportat o fitxer corrupte.")
            else:
                converted_wav_path = temp_path

            # Validar archivo WAV resultante antes de continuar
            if not os.path.exists(converted_wav_path) or os.path.getsize(converted_wav_path) < 44:
                self.logger.error(f"Generated WAV file is invalid or missing for chunk {chunk_index}", module="Transcription")
                abort(400, message="El fitxer d'àudio convertit és invàlid.")

            # Validación adicional: intentar verificar que el WAV es válido antes del análisis
            try:
                # Verificar header WAV básico
                with open(converted_wav_path, "rb") as wav_check:
                    header = wav_check.read(12)
                    if not (header.startswith(b'RIFF') and b'WAVE' in header):
                        raise ValueError("Invalid WAV header")
                        
                self.logger.info(f"WAV validation successful for chunk {chunk_index}, size: {os.path.getsize(converted_wav_path)} bytes", module="Transcription")
                
            except Exception as validation_error:
                self.logger.error(f"WAV validation failed for chunk {chunk_index}: {validation_error}", module="Transcription")
                abort(400, message="El fitxer d'àudio generat no és un WAV vàlid.")

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

            # Si es el primer chunk y tenemos header WebM guardado, agregarlo al análisis
            if chunk_index == 0 and hasattr(self, '_temp_header_data'):
                import base64
                combined_metrics['webm_header'] = base64.b64encode(self._temp_header_data).decode('utf-8')
                delattr(self, '_temp_header_data')  # Limpiar después de usar

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
            self.logger.error("Integrity violation transcribing chunk", module="Transcription", 
                            metadata={"session_id": session_id, "chunk_index": chunk_index}, error=mapped)
            abort(422, message=str(mapped))
        except subprocess.CalledProcessError as e:
            db.session.rollback()
            error_msg = f"FFmpeg conversion failed: {e.stderr[:500] if e.stderr else 'No error details'}"
            self.logger.error("FFmpeg conversion error", module="Transcription", 
                            metadata={"session_id": session_id, "chunk_index": chunk_index}, 
                            error=error_msg)
            abort(500, message=f"Error de conversió d'àudio: {str(e)}")
        except Exception as e:
            db.session.rollback()
            error_msg = f"Processing chunk {chunk_index} for session {session_id}: {str(e)}"
            self.logger.error("Unexpected error transcribing chunk", module="Transcription", 
                            metadata={"session_id": session_id, "chunk_index": chunk_index}, 
                            error=e)
            abort(500, message=f"S'ha produït un error inesperat: {str(e)}")
        finally:
            # Limpiar todos los archivos temporales
            for path in [temp_path, converted_wav_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as cleanup_error:
                        self.logger.warning(f"Could not cleanup temp file {path}: {cleanup_error}", module="Transcription")

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