import os
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
from flask_migrate import Migrate, upgrade as alembic_upgrade
from flask_smorest import Api
from sqlalchemy.engine import URL

from db import create_db

from resources.health import blp as HealthBlueprint
from resources.version import blp as VersionBlueprint
from resources.user import blp as UserBlueprint
from resources.transcription import blp as TranscriptionBlueprint
from resources.question import blp as QuestionBlueprint
from resources.activity import blp as ActivityBlueprint
from resources.documentation import blp as DocumentationBlueprint
from resources.qr import blp as QRBlueprint
from resources.report import blp as ReportBlueprint

def create_app(settings_module: str = 'globals') -> Flask:
    """
    Creates a new instace of Flask application.
    
    Args:
        settings_module (str, optional): Configuration module to use.
    """
    app = Flask(__name__)
    
    app.config.from_object(settings_module)

    DB_USER = app.config.get('DB_USER')
    DB_PASSWORD = app.config.get('DB_PASSWORD')
    DB_HOST = app.config.get('DB_HOST')
    DB_PORT = app.config.get('DB_PORT')
    DB_NAME = app.config.get('DB_NAME')

    required_db_fields = {
        "DB_USER": DB_USER,
        "DB_HOST": DB_HOST,
        "DB_NAME": DB_NAME,
    }
    missing_db_fields = [key for key, value in required_db_fields.items() if value is None]
    if missing_db_fields:
        raise RuntimeError(
            f"Falten paràmetres de configuració de base de dades per: {', '.join(missing_db_fields)}. "
            "Configura'ls a les variables d'entorn o al mòdul d'ajusts."
        )

    try:
        db_port = int(DB_PORT) if DB_PORT is not None else 5432
    except (TypeError, ValueError):
        raise RuntimeError(f"Valor de DB_PORT no vàlid: {DB_PORT!r}. Ha de ser un enter.")

    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=db_port,
        database=DB_NAME,
    )

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.render_as_string(hide_password=False)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    DB_SSL:bool = app.config.get("DB_SSL", False)
    DB_SSL_CA = app.config.get("DB_SSL_CA")
    if DB_SSL and DB_SSL_CA:
        app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
        app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] = {
            "ssl": {"ca": DB_SSL_CA}
        }
        
    CORS(
       app,
       resources={r"/api/*": {"origins": "*"}},
       allow_headers=["Content-Type", "Authorization"],
       supports_credentials=True
    )

    SWAGGER_URL = app.config.get('SWAGGER_URL')
    
    app.config['OPENAPI_VERSION'] = '3.0.3'
    app.config['OPENAPI_URL_PREFIX'] = '/'
    app.config['OPENAPI_SWAGGER_UI_PATH'] = SWAGGER_URL
    app.config['OPENAPI_SWAGGER_UI_URL'] = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/'
        
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
    
    def getApiPrefix(url:str) -> str: return f"{app.config['API_PREFIX']}/{url}"

    jwt = JWTManager(app)

    api = Api(app)
    app.extensions.setdefault("labubu", {})["api"] = api

    api.spec.components.security_scheme(
        'jwt', {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT', 'x-bearerInfoFunc': 'app.decode_token'}
    )

    api.spec.options["security"] = [{"jwt": []}]

    # HTTP routes
    api.register_blueprint(HealthBlueprint, url_prefix=getApiPrefix('health'))
    api.register_blueprint(VersionBlueprint, url_prefix=app.config['VERSION_ENDPOINT'])
    api.register_blueprint(UserBlueprint, url_prefix=getApiPrefix('user'))
    api.register_blueprint(TranscriptionBlueprint, url_prefix=getApiPrefix('transcription'))
    api.register_blueprint(QuestionBlueprint, url_prefix=getApiPrefix('question'))
    api.register_blueprint(ActivityBlueprint, url_prefix=getApiPrefix('activity'))
    api.register_blueprint(DocumentationBlueprint, url_prefix=getApiPrefix('swagger-doc'))
    api.register_blueprint(QRBlueprint, url_prefix=getApiPrefix('qr'))
    api.register_blueprint(ReportBlueprint, url_prefix=getApiPrefix('report'))
    
    # SIMPLIFIED TRANSCRIPTION ENDPOINT (bypasses flask-smorest)
    # This endpoint handles MediaRecorder WebM chunks that flask-smorest can't parse
    @app.route(f"{getApiPrefix('transcription')}/chunk-raw", methods=['POST'])
    @jwt_required()
    def upload_chunk_raw():
        """
        Simplified chunk upload that bypasses flask-smorest multipart parsing.
        Designed specifically for frontend MediaRecorder WebM chunks.
        """
        import tempfile
        import subprocess
        import json
        from helpers.debugger.logger import AbstractLogger
        from helpers.analysis_engine import analyze_audio_signal, analyze_linguistics
        from models.transcription import TranscriptionChunk
        from openai import AzureOpenAI
        
        logger = AbstractLogger.get_instance()
        
        try:
            logger.info(f"Raw chunk upload - Content-Type: {request.content_type}", module="TranscriptionRaw")
            
            # Basic validation
            if not request.content_type or 'multipart/form-data' not in request.content_type:
                return jsonify({"error": "Content-Type must be multipart/form-data"}), 400
            
            # Get form data
            session_id = request.form.get('session_id')
            chunk_index_str = request.form.get('chunk_index')
            
            if not session_id or not chunk_index_str:
                return jsonify({"error": "Missing session_id or chunk_index"}), 400
                
            try:
                chunk_index = int(chunk_index_str)
            except (ValueError, TypeError):
                return jsonify({"error": "chunk_index must be integer"}), 400
            
            # Get audio file
            if 'audio_blob' not in request.files:
                return jsonify({"error": "Missing audio_blob file"}), 400
                
            audio_file = request.files['audio_blob']
            if not audio_file or audio_file.filename == '':
                return jsonify({"error": "No file provided"}), 400
            
            logger.info(f"Processing chunk {chunk_index} for session {session_id}", module="TranscriptionRaw")
            
            # Process file
            temp_path = None
            converted_wav_path = None
            
            try:
                # Save temporary file
                suffix = os.path.splitext(audio_file.filename)[1] or ".webm"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    audio_file.save(temp_file.name)
                    temp_path = temp_file.name
                
                # Convert to WAV with validation
                if suffix != ".wav":
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
                        converted_wav_path = wav_file.name
                    
                    # Enhanced FFmpeg command with better error handling for WebM chunks
                    cmd = ["ffmpeg", "-y", "-i", temp_path, "-ac", "1", "-ar", "16000", "-f", "wav", converted_wav_path]
                    
                    try:
                        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
                        logger.info(f"FFmpeg conversion successful for chunk {chunk_index}", module="TranscriptionRaw")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"FFmpeg failed for chunk {chunk_index}: exit code {e.returncode}", module="TranscriptionRaw")
                        logger.error(f"FFmpeg stderr: {e.stderr}", module="TranscriptionRaw")
                        
                        # Check if it's a WebM chunk issue (common exit codes: 183, 69)
                        if suffix.lower() == '.webm' and e.returncode in [183, 69]:
                            logger.warning(f"Detected invalid WebM chunk {chunk_index} - likely MediaRecorder fragment", module="TranscriptionRaw")
                            return jsonify({
                                "error": f"Invalid WebM chunk {chunk_index} - MediaRecorder produced incomplete file fragment",
                                "suggestion": "This is typically caused by MediaRecorder generating streaming fragments instead of complete files"
                            }), 400
                        else:
                            return jsonify({"error": f"Audio conversion failed: {e.stderr}"}), 500
                    except subprocess.TimeoutExpired:
                        logger.error(f"FFmpeg timeout for chunk {chunk_index}", module="TranscriptionRaw")
                        return jsonify({"error": "Audio conversion timeout"}), 500
                else:
                    converted_wav_path = temp_path
                
                # Audio analysis
                acoustic_metrics = analyze_audio_signal(converted_wav_path)
                
                # Transcription
                api_key = app.config.get("AZURE_OPENAI_API_KEY")
                endpoint = app.config.get("AZURE_OPENAI_ENDPOINT")
                api_version = app.config.get("AZURE_OPENAI_API_VERSION")
                deployment = app.config.get("AZURE_OPENAI_DEPLOYMENT_NAME")
                
                client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
                
                with open(converted_wav_path, "rb") as audio_data:
                    transcript = client.audio.transcriptions.create(
                        model=deployment,
                        file=audio_data,
                        language="ca", 
                        response_format="verbose_json"
                    )
                
                text_result = transcript.text
                linguistic_metrics = analyze_linguistics(text_result)
                
                combined_metrics = {
                    **acoustic_metrics,
                    **linguistic_metrics,
                    "raw_latency": transcript.segments[0].start if transcript.segments else 0
                }
                
                # Save to database
                new_chunk = TranscriptionChunk(
                    session_id=session_id,
                    chunk_index=chunk_index,
                    text=text_result,
                    analysis=combined_metrics
                )
                db.session.add(new_chunk)
                db.session.commit()
                
                return jsonify({
                    "status": "success",
                    "partial_text": text_result,
                    "analysis": combined_metrics
                }), 200
                
            finally:
                # Cleanup
                for path in [temp_path, converted_wav_path]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
                        
        except Exception as e:
            logger.error(f"Raw endpoint error: {e}", module="TranscriptionRaw")
            return jsonify({"error": str(e)}), 500

    with app.app_context():
        db = create_db(app)
        import models
        migrate = Migrate(app, db)
        DB_AUTO_MIGRATE = app.config.get("DB_AUTO_MIGRATE", False)
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if DB_AUTO_MIGRATE and os.path.isdir(migrations_dir) and os.path.isfile(os.path.join(migrations_dir, "env.py")):
            alembic_upgrade()
    
    ## NotImplementedError
    @app.errorhandler(NotImplementedError)
    def handle_not_implemented_error(error):
        response = {
            "error_message": str(error),
            "code": 501,
            "status": "No implementat"
        }
        return jsonify(response), 501
    
    ## BadRequest - Multipart parsing errors from frontend WebM chunks
    @app.errorhandler(400)
    def handle_bad_request_error(error):
        """Handle flask-smorest multipart parsing errors specifically for WebM chunks."""
        from helpers.debugger.logger import AbstractLogger
        logger = AbstractLogger.get_instance()
        
        error_description = getattr(error, 'description', str(error))
        error_data = getattr(error, 'data', None)
        if isinstance(error_data, dict):
            data_message = error_data.get("message")
            if data_message:
                error_description = str(data_message)
        logger.error(f"App-level 400 error: {error_description}", module="App")
        
        # Specific handling for the problematic frontend WebM parsing error
        if "could not understand" in error_description.lower() or "browser" in error_description.lower():
            response = {
                "code": 400,
                "message": "Error de format WebM del frontend. MediaRecorder està enviant chunks incompatibles amb el backend.",
                "status": "Bad Request",
                "technical_details": "Frontend MediaRecorder chunks may be malformed or missing headers",
                "suggestion": "Verify WebM chunk generation in frontend or switch to MP3 format"
            }
            return jsonify(response), 400
        
        # Standard 400 error handling
        response = {
            "code": 400,
            "message": error_description,
            "status": "Bad Request"
        }
        return jsonify(response), 400
    
    @app.route('/')
    def main_page():
        """Redirects to the Swagger UI documentation."""
        return redirect(app.config['OPENAPI_SWAGGER_UI_PATH'], code=302)
    
    return app

app = create_app(os.getenv('SETTINGS_MODULE', 'globals'))

if __name__ == "__main__":
    import inspect

    run_kwargs = dict(
        threaded=True,
        host="0.0.0.0",
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False),
        use_reloader=app.config.get('DEBUG', False),
    )

    if "allow_unsafe_werkzeug" in inspect.signature(app.run).parameters:
        run_kwargs["allow_unsafe_werkzeug"] = True

    app.run(**run_kwargs)
