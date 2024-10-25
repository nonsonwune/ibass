# app/models/user.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event, func
from .base import BaseModel
from ..extensions import db

class User(UserMixin, BaseModel):
    __tablename__ = 'users'
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, default=0, nullable=False, index=True)
    
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='voter', lazy=True, cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', backref='user', lazy=True, cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def normalize_username(username):
        """Convert username to lowercase for case-insensitive comparison"""
        return username.lower() if username else None

    def __init__(self, **kwargs):
        if 'username' in kwargs:
            kwargs['username'] = self.normalize_username(kwargs['username'])
        super(User, self).__init__(**kwargs)

    def calculate_score(self):
        return sum(comment.score for comment in self.comments)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)