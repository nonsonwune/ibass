# app/models/user.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event, func
from ..extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Integer, default=0, nullable=True)
    is_verified = db.Column(db.Integer, default=0, nullable=True)
    score = db.Column(db.Integer, default=0, nullable=False, index=True)
    
    # Relationships remain unchanged
    comments = db.relationship("Comment", backref="author", lazy=True, cascade="all, delete-orphan")
    votes = db.relationship("Vote", backref="voter", lazy=True, cascade="all, delete-orphan")
    feedback = db.relationship("Feedback", backref="user", lazy=True, cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Set the password hash for the user"""
        self.password = generate_password_hash(password)
        
    def check_password(self, password):
        """Verify the password against the stored hash"""
        return check_password_hash(self.password, password)

    @staticmethod
    def normalize_username(username):
        """Convert username to lowercase for case-insensitive comparison"""
        return username.lower() if username else None

    def __init__(self, **kwargs):
        # Handle password hashing if password is provided
        if 'password' in kwargs:
            password = kwargs.pop('password')
            kwargs['password'] = generate_password_hash(password)
            
        # Convert boolean inputs to integers for database storage
        if 'is_admin' in kwargs:
            kwargs['is_admin'] = 1 if kwargs['is_admin'] else 0
        if 'is_verified' in kwargs:
            kwargs['is_verified'] = 1 if kwargs['is_verified'] else 0
        if 'username' in kwargs:
            kwargs['username'] = self.normalize_username(kwargs['username'])
        
        super(User, self).__init__(**kwargs)

    def calculate_score(self):
        return sum(comment.score for comment in self.comments)

    @property
    def is_admin_bool(self):
        """Return the boolean value directly"""
        return self.is_admin

    @property
    def is_verified_bool(self):
        """Return the boolean value directly"""
        return self.is_verified