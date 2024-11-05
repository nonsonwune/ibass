# app/models/subject.py
from ..extensions import db
from .base import BaseModel

class Subjects(BaseModel):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('subject_categories.id'), nullable=False)
    is_core = db.Column(db.Boolean, default=False)
    
    category = db.relationship('SubjectCategories', back_populates='subjects')
    
    def __repr__(self):
        return f'<Subject {self.name}>'

class SubjectCategories(BaseModel):
    __tablename__ = 'subject_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    
    subjects = db.relationship('Subjects', back_populates='category')
    
    def __repr__(self):
        return f'<SubjectCategory {self.name}>'