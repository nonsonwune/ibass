# add_admin_user.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from flask_login import UserMixin
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Set the same configuration as your main app
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",  # Match your main app's environment variable name
    "postgresql://nonsonwune:password@localhost:5432/university_courses",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define User model matching the main app
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Integer, default=0, nullable=True)
    is_verified = db.Column(db.Integer, default=0, nullable=True)
    score = db.Column(db.Integer, default=0, nullable=False, index=True)

    @staticmethod
    def normalize_username(username):
        """Convert username to lowercase for case-insensitive comparison"""
        return username.lower() if username else None

def add_admin_user(username, email, password):
    with app.app_context():
        # Normalize username
        normalized_username = User.normalize_username(username)
        
        # Check if the user already exists
        existing_user = User.query.filter_by(username=normalized_username).first()
        if existing_user:
            print(f"User '{username}' already exists.")
            return

        # Create new admin user with proper integer values
        hashed_password = generate_password_hash(password)
        new_admin = User(
            username=normalized_username,
            email=email,
            password=hashed_password,
            is_admin=1,  # Use 1 instead of True
            is_verified=1  # Admins should be verified by default
        )

        try:
            # Add to database
            db.session.add(new_admin)
            db.session.commit()
            print(f"Admin user '{username}' created successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python add_admin_user.py <username> <email> <password>")
        sys.exit(1)

    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]

    add_admin_user(username, email, password)