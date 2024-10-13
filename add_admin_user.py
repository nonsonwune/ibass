from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from flask_login import UserMixin
import sys

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///university_courses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy with the app
db = SQLAlchemy()
db.init_app(app)


# Define User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


def add_admin_user(username, email, password):
    with app.app_context():
        # Check if the user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"User '{username}' already exists.")
            return

        # Create new admin user
        hashed_password = generate_password_hash(password)
        new_admin = User(
            username=username, email=email, password=hashed_password, is_admin=True
        )

        # Add to database
        db.session.add(new_admin)
        db.session.commit()

        print(f"Admin user '{username}' created successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python add_admin_user.py <username> <email> <password>")
        sys.exit(1)

    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]

    add_admin_user(username, email, password)
