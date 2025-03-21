# app/config.py
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # -------------------------------
    # Logging Configuration
    # -------------------------------
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SQLALCHEMY_LOG_LEVEL = os.getenv('SQLALCHEMY_LOG_LEVEL', 'WARNING')

    # -------------------------------
    # Debug Configuration
    # -------------------------------
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'

    # -------------------------------
    # Secret Key Configuration
    # -------------------------------
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')

    # -------------------------------
    # Instance Path Configuration
    # -------------------------------
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_PATH = os.path.join(BASE_DIR, '../instance')
    os.makedirs(INSTANCE_PATH, exist_ok=True)

    # -------------------------------
    # Database Configuration
    # -------------------------------
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    if not SQLALCHEMY_DATABASE_URI:
        logging.error("Database URI not found in environment variables!")
        raise ValueError("Database URI must be set in environment variables")
    

    # -------------------------------
    # SQLAlchemy Configuration
    # -------------------------------
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Disable SQL echo by default
    
    # Configure connection pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            # Only require SSL for production database
            'sslmode': 'require' if 'render.com' in os.getenv('SQLALCHEMY_DATABASE_URI', '') else 'disable'
        }
    }

    # -------------------------------
    # Mail Configuration
    # -------------------------------
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    if not all([MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER]):
        logging.warning("Mail configuration incomplete. Email features may not work.")

    # -------------------------------
    # Programme Groups Configuration
    # -------------------------------
    PROGRAMME_GROUPS = {
        "ALL_DEGREE_AWARDING_INSTITUTIONS": [
            "E-LEARNING UNIVERSITIES OF NIGERIA",
            "FEDERAL UNIVERSITIES",
            "FEDERAL UNIVERSITIES OF AGRICULTURE",
            "FEDERAL UNIVERSITIES OF HEALTH SCIENCES",
            "FEDERAL UNIVERSITIES OF TECHNOLOGY",
            "OPEN AND DISTANCE LEARNING PROGRAMMES",
            "OTHER DEGREE AWARDING INSTITUTIONS",
            "PRIVATE UNIVERSITIES",
            "SANDWICH PROGRAMMES",
            "STATE UNIVERSITIES",
            "STATE UNIVERSITIES OF AGRICULTURE",
            "STATE UNIVERSITIES OF MEDICAL SCIENCES",
            "STATE UNIVERSITIES OF TECHNOLOGY",
        ],
        "ALL_NCE": [
            "FEDERAL COLLEGES OF EDUCATION",
            "STATE COLLEGES OF EDUCATION",
            "PRIVATE COLLEGES OF EDUCATION",
        ],
    }

    # CSRF Protection Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Exclude GET requests
    WTF_CSRF_SSL_STRICT = True
    WTF_CSRF_CHECK_DEFAULT = True