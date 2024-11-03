# app/models/requirement.py
from datetime import datetime
from ..extensions import db
from sqlalchemy.ext.hybrid import hybrid_property

class CourseRequirementTemplates(db.Model):
    __tablename__ = 'course_requirement_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    min_credits = db.Column(db.Integer, nullable=False, default=5)
    max_sittings = db.Column(db.Integer, nullable=False, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject_requirements = db.relationship('TemplateSubjectRequirements',
                                        backref='template',
                                        lazy='dynamic',
                                        cascade='all, delete-orphan')
    
    institution_requirements = db.relationship('InstitutionRequirements',
                                            backref='template',
                                            lazy='dynamic',
                                            cascade='all, delete-orphan')

    def __repr__(self):
        return f'<CourseTemplate {self.name}>'

    @hybrid_property
    def mandatory_subjects(self):
        """Get all mandatory subjects for this template."""
        return [req.subject for req in self.subject_requirements.filter_by(is_mandatory=True)]

    @hybrid_property
    def optional_subjects(self):
        """Get all optional subjects for this template."""
        return [req.subject for req in self.subject_requirements.filter_by(is_mandatory=False)]

    def to_dict(self):
        """Convert template to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'min_credits': self.min_credits,
            'max_sittings': self.max_sittings,
            'mandatory_subjects': [
                {'id': s.id, 'name': s.name} for s in self.mandatory_subjects
            ],
            'optional_subjects': [
                {'id': s.id, 'name': s.name} for s in self.optional_subjects
            ]
        }

class TemplateSubjectRequirements(db.Model):
    __tablename__ = 'template_subject_requirements'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('course_requirement_templates.id', ondelete='CASCADE'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'))
    is_mandatory = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('template_id', 'subject_id', name='unique_template_subject'),
    )

    def __repr__(self):
        return f'<TemplateRequirement {self.template_id}:{self.subject_id}>'

class InstitutionRequirements(db.Model):
    __tablename__ = 'institution_requirements'

    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'))
    template_id = db.Column(db.Integer, db.ForeignKey('course_requirement_templates.id', ondelete='CASCADE'))
    override_min_credits = db.Column(db.Integer)
    override_max_sittings = db.Column(db.Integer)
    additional_requirements = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject_requirements = db.relationship('InstitutionSubjectRequirements',
                                        backref='institution_requirement',
                                        lazy='dynamic',
                                        cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('institution_id', 'template_id', name='unique_institution_template'),
        db.CheckConstraint('override_min_credits IS NULL OR override_min_credits > 0', 
                          name='valid_override_credits'),
        db.CheckConstraint('override_max_sittings IS NULL OR override_max_sittings > 0',
                          name='valid_override_sittings')
    )

    def __repr__(self):
        return f'<InstitutionRequirement {self.institution_id}:{self.template_id}>'

    @hybrid_property
    def effective_min_credits(self):
        """Get effective minimum credits (override or template default)."""
        return self.override_min_credits or self.template.min_credits

    @hybrid_property
    def effective_max_sittings(self):
        """Get effective maximum sittings (override or template default)."""
        return self.override_max_sittings or self.template.max_sittings

    def to_dict(self):
        """Convert requirements to dictionary format."""
        return {
            'id': self.id,
            'institution_id': self.institution_id,
            'template_id': self.template_id,
            'min_credits': self.effective_min_credits,
            'max_sittings': self.effective_max_sittings,
            'additional_requirements': self.additional_requirements,
            'mandatory_subjects': [
                {'id': req.subject.id, 'name': req.subject.name}
                for req in self.subject_requirements.filter_by(is_mandatory=True)
            ],
            'optional_subjects': [
                {'id': req.subject.id, 'name': req.subject.name}
                for req in self.subject_requirements.filter_by(is_mandatory=False)
            ]
        }

class InstitutionSubjectRequirements(db.Model):
    __tablename__ = 'institution_subject_requirements'

    id = db.Column(db.Integer, primary_key=True)
    institution_requirement_id = db.Column(db.Integer, 
                                        db.ForeignKey('institution_requirements.id', ondelete='CASCADE'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'))
    is_mandatory = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('institution_requirement_id', 'subject_id',
                           name='unique_institution_subject'),
    )

    def __repr__(self):
        return f'<InstitutionSubjectRequirement {self.institution_requirement_id}:{self.subject_id}>'