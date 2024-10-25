# app/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # -------------------------------
    # Secret Key Configuration
    # -------------------------------
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')

    # -------------------------------
    # Instance Path Configuration
    # -------------------------------
    # Get the absolute path to the current file
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # Define the instance folder path relative to BASE_DIR
    INSTANCE_PATH = os.path.join(BASE_DIR, '../instance')

    # Ensure the instance folder exists
    os.makedirs(INSTANCE_PATH, exist_ok=True)

    # -------------------------------
    # Database Configuration
    # -------------------------------
    # Database URI from environment variable or default to SQLite
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'SQLALCHEMY_DATABASE_URI',
        f'sqlite:///{os.path.join(INSTANCE_PATH, "university_courses.db")}'
    )

    # Log the database URI for debugging purposes
    print(f"Using Database URI: {SQLALCHEMY_DATABASE_URI}")

    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Set to False in production

    # -------------------------------
    # Mail Configuration
    # -------------------------------
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').strip().lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True').strip().lower() in ['true', '1', 't']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

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

    # Set transaction isolation level and other engine options
    SQLALCHEMY_ENGINE_OPTIONS = {
        'isolation_level': 'SERIALIZABLE',
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,  # 30 seconds
        'pool_recycle': 1800,  # 30 minutes
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Set to False in production