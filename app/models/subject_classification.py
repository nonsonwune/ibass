# app/models/subject_classification.py
from datetime import datetime
from ..extensions import db
from .base import BaseModel
from .subject import Subjects

class SubjectCategoryTypes(BaseModel):
    __tablename__ = 'subject_category_types'
    
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    classifications = db.relationship('SubjectClassifications', back_populates='category_type')
    
    def __repr__(self):
        return f'<SubjectCategoryType {self.type_name}>'

class SubjectClassifications(BaseModel):
    __tablename__ = 'subject_classifications'
    
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False)
    category_type_id = db.Column(db.Integer, db.ForeignKey('subject_category_types.id'))
    parent_category_id = db.Column(db.Integer, db.ForeignKey('subject_classifications.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    category_type = db.relationship('SubjectCategoryTypes', back_populates='classifications')
    parent_category = db.relationship('SubjectClassifications', remote_side=[id], backref='child_categories')
    classified_subjects = db.relationship('ClassifiedSubjects', back_populates='classification')
    
    def __repr__(self):
        return f'<SubjectClassification {self.category_name}>'

class ClassifiedSubjects(BaseModel):
    __tablename__ = 'classified_subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    classification_id = db.Column(db.Integer, db.ForeignKey('subject_classifications.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    classification = db.relationship('SubjectClassifications', back_populates='classified_subjects')
    subject = db.relationship('Subjects')
    
    def __repr__(self):
        return f'<ClassifiedSubject classification_id={self.classification_id} subject_id={self.subject_id}>'
