import os
from dotenv import load_dotenv

VERSION = '0.3.0'

DEFAULT_VERSION_ENDPOINT = '/api/version'

DEFAULT_API_PREFIX = '/api/v1'
DEFAULT_API_TITLE = 'Labubu API'
DEFAULT_SWAGGER_URL = '/api-docs'
DEFAULT_DEBUG = False
DEFAULT_PORT = 5000
DEFAULT_DB_PORT = 5432

#------------------------------

load_dotenv()

VERSION_ENDPOINT = os.getenv('VERSION_ENDPOINT', DEFAULT_VERSION_ENDPOINT)
API_PREFIX=os.getenv('API_PREFIX', DEFAULT_API_PREFIX)
API_TITLE=os.getenv('API_TITLE', DEFAULT_API_TITLE)
API_VERSION=os.getenv('API_VERSION', VERSION)
SWAGGER_URL=os.getenv('SWAGGER_URL', DEFAULT_SWAGGER_URL)
DEBUG = str(os.getenv('DEBUG', DEFAULT_DEBUG)).lower() in ('t', 'true', '1', 'y', 'yes')
PORT = int(os.getenv('PORT', DEFAULT_PORT))
HOST_NAME = os.getenv('HOST_NAME', f'http://localhost:{PORT}')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT', DEFAULT_DB_PORT))
DB_HOST = os.getenv('DB_HOST')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_USER = os.getenv('DB_USER')
DB_SSL = os.getenv("DB_SSL", "false").lower() == "true"
DB_SSL_CA = os.getenv("DB_SSL_CA")
DB_AUTO_MIGRATE = str(os.getenv('DB_AUTO_MIGRATE', '0')).lower() in ('t', 'true', '1', 'y', 'yes')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_TOKEN_LOCATION = os.getenv('JWT_TOKEN_LOCATION', 'headers').split(',')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
AZURE_OPENAI_LLM_MODEL = os.getenv('AZURE_OPENAI_LLM_MODEL', 'gpt-5-mini')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.5-flash')

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
APPLICATION_EMAIL = os.getenv('APPLICATION_EMAIL')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
RESET_PASSWORD_FRONTEND_PATH = FRONTEND_URL + os.getenv('RESET_PASSWORD_FRONTEND_PATH', '/reset-password')
RESET_CODE_VALIDITY_MINUTES = 5

EMAIL_ADAPTER_PROVIDER = os.getenv('EMAIL_ADAPTER_PROVIDER', 'smtp').lower()

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_USE_TLS = str(os.getenv('SMTP_USE_TLS', 'true')).lower() in ('t', 'true', '1', 'y', 'yes')
SMTP_USE_SSL = str(os.getenv('SMTP_USE_SSL', 'false')).lower() in ('t', 'true', '1', 'y', 'yes')
