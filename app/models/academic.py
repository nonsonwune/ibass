from datetime import datetime
from ..extensions import db
from .base import BaseModel
from sqlalchemy.dialects.postgresql import JSONB

# ClassifiedSubject model has been moved to subject_classification.py as ClassifiedSubjects

class CertificationHierarchy(BaseModel):
    __tablename__ = 'certification_hierarchies'
    
    id = db.Column(db.Integer, primary_key=True)
    certification_type = db.Column(db.String(100))
    certification_name = db.Column(db.String(255))
    hierarchy_level = db.Column(db.Integer)
    equivalency_details = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('certification_type', 'certification_name'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'certification_type': self.certification_type,
            'certification_name': self.certification_name,
            'hierarchy_level': self.hierarchy_level,
            'equivalency_details': self.equivalency_details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CatchmentArea(BaseModel):
    __tablename__ = 'catchment_area'
    
    id = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(20), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    university = db.relationship('University', backref=db.backref('catchment_areas', lazy=True))
    states = db.relationship('State', secondary='catchment_state', backref='catchment_areas')
    
    __table_args__ = (
        db.UniqueConstraint('university_id', 'region'),
        db.Index('idx_catchment_area_university', 'university_id'),
        db.Index('idx_catchment_area_region', 'region')
    )

class CatchmentState(BaseModel):
    __tablename__ = 'catchment_state'
    
    id = db.Column(db.Integer, primary_key=True)
    catchment_area_id = db.Column(db.Integer, db.ForeignKey('catchment_area.id', ondelete='CASCADE'))
    state_id = db.Column(db.Integer, db.ForeignKey('state.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('catchment_area_id', 'state_id'),
    )

class AlternativeQualification(BaseModel):
    __tablename__ = 'alternative_qualifications'
    
    id = db.Column(db.Integer, primary_key=True)
    qualification_type = db.Column(db.String(100))
    qualification_name = db.Column(db.String(255))
    accepted_subjects = db.Column(db.ARRAY(db.Text))
    conditions = db.Column(db.Text)
    hierarchy_level = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('qualification_type', 'qualification_name'),
    )
    
    @property
    def formatted_subjects(self):
        """Get accepted subjects as a formatted list."""
        return [subj.strip() for subj in self.accepted_subjects] if self.accepted_subjects else []

class AcademicRequirement(BaseModel):
    __tablename__ = 'academic_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('course_requirement_template.id', ondelete='CASCADE'))
    minimum_credits = db.Column(db.Integer, default=5)
    maximum_sittings = db.Column(db.Integer, default=2)
    mandatory_subjects = db.Column(db.ARRAY(db.Text))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    template = db.relationship('CourseRequirementTemplate', backref=db.backref('academic_requirements', lazy=True))
    
    @property
    def formatted_subjects(self):
        """Get mandatory subjects as a formatted list."""
        return [subj.strip() for subj in self.mandatory_subjects] if self.mandatory_subjects else []
    
    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'minimum_credits': self.minimum_credits,
            'maximum_sittings': self.maximum_sittings,
            'mandatory_subjects': self.formatted_subjects,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# TeachingRequirement model has been moved to requirement.py

class SubjectEquivalency(BaseModel):
    __tablename__ = 'subject_equivalencies'
    
    id = db.Column(db.Integer, primary_key=True)
    primary_subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'))
    equivalent_subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'))
    conditions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    primary_subject = db.relationship(
        'Subjects',
        foreign_keys=[primary_subject_id],
        backref=db.backref('equivalent_subjects', lazy='dynamic'),
        lazy='joined'
    )
    equivalent_subject = db.relationship(
        'Subjects',
        foreign_keys=[equivalent_subject_id],
        backref=db.backref('primary_subjects', lazy='dynamic'),
        lazy='joined'
    )
    
    __table_args__ = (
        db.UniqueConstraint('primary_subject_id', 'equivalent_subject_id', 
            name='subject_equivalencies_primary_subject_id_equivalent_subject_key'),
        db.Index('idx_subject_equiv_primary', 'primary_subject_id'),
        db.Index('idx_subject_equiv_equivalent', 'equivalent_subject_id')
    )
    
    def __repr__(self):
        return f'<SubjectEquivalency {self.primary_subject.name} -> {self.equivalent_subject.name}>'
    
    def to_dict(self):
        """Convert equivalency to dictionary format."""
        return {
            'id': self.id,
            'primary_subject': {
                'id': self.primary_subject_id,
                'name': self.primary_subject.name if self.primary_subject else None,
                'category': self.primary_subject.category.name if self.primary_subject and self.primary_subject.category else None
            },
            'equivalent_subject': {
                'id': self.equivalent_subject_id,
                'name': self.equivalent_subject.name if self.equivalent_subject else None,
                'category': self.equivalent_subject.category.name if self.equivalent_subject and self.equivalent_subject.category else None
            },
            'conditions': self.conditions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_equivalents_for_subject(cls, subject_id):
        """Get all equivalent subjects for a given subject."""
        return cls.query.filter_by(primary_subject_id=subject_id)\
            .options(db.joinedload(cls.equivalent_subject))\
            .all()
    
    @classmethod
    def get_all_with_subjects(cls):
        """Get all equivalencies with related subject information."""
        return cls.query\
            .options(
                db.joinedload(cls.primary_subject),
                db.joinedload(cls.equivalent_subject)
            )\
            .all()
    
    @classmethod
    def check_equivalency(cls, subject_id1, subject_id2):
        """Check if two subjects are equivalent."""
        return cls.query.filter(
            db.or_(
                db.and_(
                    cls.primary_subject_id == subject_id1,
                    cls.equivalent_subject_id == subject_id2
                ),
                db.and_(
                    cls.primary_subject_id == subject_id2,
                    cls.equivalent_subject_id == subject_id1
                )
            )
        ).first() is not None 