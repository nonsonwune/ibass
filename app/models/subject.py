# app/models/subject.py
from datetime import datetime
from ..extensions import db
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property

class SubjectCategories(db.Model):
    __tablename__ = 'subject_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('subject_categories.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('SubjectCategories', remote_side=[id])
    subjects = db.relationship('Subjects', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<SubjectCategory {self.name}>'

class Subjects(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('subject_categories.id'), nullable=False)
    is_core = db.Column(db.Boolean, default=False)
    alternative_names = db.Column(ARRAY(db.String))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    template_requirements = db.relationship('TemplateSubjectRequirements', 
                                         backref='subject', 
                                         lazy='dynamic',
                                         cascade='all, delete-orphan')
    
    institution_requirements = db.relationship('InstitutionSubjectRequirements',
                                            backref='subject',
                                            lazy='dynamic',
                                            cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('name', 'category_id', name='unique_subject_per_category'),
    )

    def __repr__(self):
        return f'<Subject {self.name}>'

    @classmethod
    def find_by_name(cls, name, create_if_missing=False):
        """Find a subject by name, optionally creating if it doesn't exist."""
        subject = cls.query.filter(
            db.func.lower(cls.name) == db.func.lower(name)
        ).first()
        
        if not subject and create_if_missing:
            subject = cls(name=name)
            db.session.add(subject)
            db.session.flush()
            
        return subject