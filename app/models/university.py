# app/models/university.py
from .base import BaseModel
from ..extensions import db
from sqlalchemy import func

class University(BaseModel):
    __tablename__ = 'university'
    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(256), unique=True, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    program_type = db.Column(db.String(50), nullable=False)
    website = db.Column(db.String(255))
    established = db.Column(db.Integer)
    
    courses = db.relationship(
        'Course', 
        backref='university', 
        lazy=True,
        primaryjoin="University.university_name == Course.university_name",
        cascade='all, delete-orphan'
    )

    @classmethod
    def get_all_states(cls):
        """Retrieve all unique states from universities"""
        return [state[0] for state in 
                db.session.query(cls.state)
                .distinct()
                .order_by(cls.state)
                .all()]

class Course(BaseModel):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(256), nullable=False)
    university_name = db.Column(db.String(256), db.ForeignKey('university.university_name'), nullable=False)
    abbrv = db.Column(db.Text)
    direct_entry_requirements = db.Column(db.Text)
    utme_requirements = db.Column(db.Text)
    subjects = db.Column(db.Text)