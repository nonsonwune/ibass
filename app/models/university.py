# app/models/university.py
from .base import BaseModel
from ..extensions import db
import logging

class University(BaseModel):
    __tablename__ = 'universities'
    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(256), unique=True, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    program_type = db.Column(db.String(50), nullable=False)
    website = db.Column(db.String(255))
    established = db.Column(db.Integer)
    
    courses = db.relationship('Course', backref='university', lazy=True, cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='university', lazy=True, cascade='all, delete-orphan')

    @classmethod
    def get_all_states(cls):
        states = cls.query.with_entities(cls.state).distinct().order_by(cls.state).all()
        logging.info(f"Retrieved {len(states)} states from database")
        return [state[0] for state in states]

class Course(BaseModel):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(256), nullable=False)
    university_name = db.Column(db.String(256), db.ForeignKey('universities.university_name'), nullable=False)
    abbrv = db.Column(db.Text)
    direct_entry_requirements = db.Column(db.Text)
    utme_requirements = db.Column(db.Text)
    subjects = db.Column(db.Text)
    bookmarks = db.relationship('Bookmark', backref='course', lazy=True, cascade='all, delete-orphan')