import os
from flask import Flask, jsonify, redirect
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate, upgrade as alembic_upgrade
from flask_smorest import Api
from sqlalchemy.engine import URL

from db import create_db

from resources.health import blp as HealthBlueprint
from resources.version import blp as VersionBlueprint
from resources.user import blp as UserBlueprint
from resources.transcription import blp as TranscriptionBlueprint

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
            f"Missing database configuration for: {', '.join(missing_db_fields)}. "
            "Set them in your environment variables or settings module."
        )

    try:
        db_port = int(DB_PORT) if DB_PORT is not None else 5432
    except (TypeError, ValueError):
        raise RuntimeError(f"Invalid DB_PORT value: {DB_PORT!r}. It must be an integer.")

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

    api.spec.components.security_scheme(
        'jwt', {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT', 'x-bearerInfoFunc': 'app.decode_token'}
    )

    api.spec.options["security"] = [{"jwt": []}]

    # HTTP routes
    api.register_blueprint(HealthBlueprint, url_prefix=getApiPrefix('health'))
    api.register_blueprint(VersionBlueprint, url_prefix=app.config['VERSION_ENDPOINT'])
    api.register_blueprint(UserBlueprint, url_prefix=getApiPrefix('user'))
    api.register_blueprint(TranscriptionBlueprint, url_prefix=getApiPrefix('transcription'))

    with app.app_context():
        db = create_db(app)
        import models
        migrate = Migrate(app, db)
        DB_AUTO_MIGRATE = app.config.get("DB_AUTO_MIGRATE", True)
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if DB_AUTO_MIGRATE and os.path.isdir(migrations_dir) and os.path.isfile(os.path.join(migrations_dir, "env.py")):
            alembic_upgrade()
    
    ## NotImplementedError
    @app.errorhandler(NotImplementedError)
    def handle_not_implemented_error(error):
        response = {
            "error_message": str(error),
            "code": 501,
            "status": "Not Implemented"
        }
        return jsonify(response), 501
    
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
