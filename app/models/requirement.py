# app/models/requirement.py
from ..extensions import db
from .base import BaseModel
from sqlalchemy import exc
from contextlib import contextmanager
import logging
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from datetime import datetime
from sqlalchemy.dialects.postgresql import TSVECTOR

logger = logging.getLogger(__name__)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    try:
        yield db.session
        db.session.commit()
    except:
        db.session.rollback()
        raise
    finally:
        db.session.close()

class UTMERequirementTemplate(BaseModel):
    __tablename__ = 'utme_requirement_template'
    
    id = db.Column(db.Integer, primary_key=True)
    requirements = db.Column(db.Text, nullable=False, unique=True)
    
    course_requirements = db.relationship('CourseRequirement', 
                                        back_populates='utme_template',
                                        lazy='dynamic')
    
class DirectEntryRequirementTemplate(BaseModel):
    __tablename__ = 'direct_entry_requirement_template'
    
    id = db.Column(db.Integer, primary_key=True)
    requirements = db.Column(db.Text, nullable=False, unique=True)
    
    course_requirements = db.relationship('CourseRequirement', 
                                        back_populates='de_template',
                                        lazy='dynamic')
class CourseRequirement(BaseModel):
    __tablename__ = 'course_requirement'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    utme_template_id = db.Column(db.Integer, db.ForeignKey('utme_requirement_template.id'))
    de_template_id = db.Column(db.Integer, db.ForeignKey('direct_entry_requirement_template.id'))
    
    # Relationships
    university = db.relationship('University', back_populates='course_requirements')
    course = db.relationship('Course', back_populates='requirements')
    subject_requirement = db.relationship(
        'SubjectRequirement', 
        back_populates='requirement',
        uselist=False,
        cascade='all, delete-orphan',
        single_parent=True 
    )
    utme_template = db.relationship(
        'UTMERequirementTemplate', 
        back_populates='course_requirements',
        lazy='select'
    )
    de_template = db.relationship(
        'DirectEntryRequirementTemplate', 
        back_populates='course_requirements',
        lazy='select'
    )
    
    __table_args__ = (
        db.Index('idx_course_requirement_composite', 'course_id', 'university_id'),
        db.Index('idx_course_requirement_course_id', 'course_id'),
        db.Index('idx_course_requirement_template_ids', 'utme_template_id', 'de_template_id'),
        db.UniqueConstraint('course_id', 'university_id', name='uq_course_university')
    )

    @property
    def utme_requirements(self):
        """Get UTME requirements text with error handling."""
        try:
            return self.utme_template.requirements if self.utme_template else None
        except Exception as e:
            logger.error(f"Error accessing UTME requirements: {str(e)}")
            return None

    @property
    def direct_entry_requirements(self):
        """Get Direct Entry requirements text with error handling."""
        try:
            return self.de_template.requirements if self.de_template else None
        except Exception as e:
            logger.error(f"Error accessing DE requirements: {str(e)}")
            return None

    def get_subjects(self):
        """Get subject requirements with error handling."""
        try:
            return self.subject_requirement.subjects if self.subject_requirement else None
        except Exception as e:
            logger.error(f"Error accessing subject requirements: {str(e)}")
            return None

    def to_dict(self):
        """Convert requirement to dictionary format."""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'university_id': self.university_id,
            'utme_requirements': self.utme_requirements,
            'direct_entry_requirements': self.direct_entry_requirements,
            'subjects': self.get_subjects()
        }

    @classmethod
    def get_course_requirements(cls, university_id, course_id=None):
        """Get requirements for a university/course combination."""
        try:
            from sqlalchemy.orm import joinedload
            query = cls.query.filter_by(university_id=university_id)
            if course_id:
                query = query.filter_by(course_id=course_id)
                
            requirements = query.options(
                joinedload(cls.utme_template),
                joinedload(cls.de_template),
                joinedload(cls.subject_requirement)
            ).all()
            
            # Add detailed logging
            logger.info(f"Found {len(requirements)} requirements for university {university_id}")
            for req in requirements:
                logger.debug(
                    f"Requirement for course {req.course_id}: "
                    f"UTME template: {req.utme_template_id}, "
                    f"DE template: {req.de_template_id}, "
                    f"Has subjects: {bool(req.subject_requirement)}"
                )
                
            return requirements
        except Exception as e:
            logger.error(f"Error fetching requirements: {str(e)}")
            return []

    @classmethod
    def copy_course_requirements(cls, source_course_id, target_course_id):
        """Copy course requirements from source to target."""
        try:
            with session_scope() as session:
                # Validate course IDs
                from .university import Course
                source_course = Course.query.get(source_course_id)
                target_course = Course.query.get(target_course_id)
                
                if not source_course or not target_course:
                    return False, "Invalid course ID(s)"
                
                if source_course_id == target_course_id:
                    return False, "Source and target courses cannot be the same"
                
                # Get source requirements
                source_requirements = cls.query.filter_by(course_id=source_course_id).all()
                if not source_requirements:
                    return False, "No requirements found for source course"
                
                # Delete existing target requirements
                cls.query.filter_by(course_id=target_course_id).delete()
                
                # Copy requirements
                for req in source_requirements:
                    new_req = cls(
                        course_id=target_course_id,
                        university_id=req.university_id,
                        utme_template_id=req.utme_template_id,
                        de_template_id=req.de_template_id
                    )
                    session.add(new_req)
                    
                    # Copy subject requirements
                    if req.subject_requirement:
                        new_subject_req = SubjectRequirement(
                            subjects=req.subject_requirement.subjects
                        )
                        new_req.subject_requirement = new_subject_req
                
                return True, "Requirements copied successfully"
                
        except exc.IntegrityError as e:
            logger.error(f"Database integrity error: {str(e)}")
            return False, "Database integrity error occurred"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return False, f"An error occurred: {str(e)}"
        
class SubjectRequirement(BaseModel):
    __tablename__ = 'subject_requirement'
    
    id = db.Column(db.Integer, primary_key=True)
    course_requirement_id = db.Column(
        db.Integer, 
        db.ForeignKey('course_requirement.id', ondelete='CASCADE'),
        nullable=False
    )
    subjects = db.Column(db.Text)
    
    requirement = db.relationship(
        'CourseRequirement',
        back_populates='subject_requirement',
        single_parent=True
    )
    
class CourseRequirementTemplate(BaseModel):
    __tablename__ = 'course_requirement_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    min_credits = db.Column(db.Integer, default=5)
    max_sittings = db.Column(db.Integer, default=2)
    
class InstitutionalVariation(BaseModel):
    __tablename__ = 'institutional_variations'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'))
    variation_type = db.Column(db.String(100))
    requirements = db.Column(db.JSON)
    conditions = db.Column(db.ARRAY(db.Text))
    search_vector = db.Column(TSVECTOR)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    university = db.relationship(
        'University', 
        backref=db.backref('variations', lazy=True, cascade='all, delete-orphan')
    )
    
    __table_args__ = (
        db.Index('idx_inst_variations_search', 'search_vector', postgresql_using='gin'),
        db.Index('idx_institutional_variations_univ', 'university_id'),
    )

    def to_dict(self):
        """Convert variation to dictionary format."""
        return {
            'id': self.id,
            'university_id': self.university_id,
            'variation_type': self.variation_type,
            'requirements': self.requirements,
            'conditions': self.conditions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    @classmethod
    def get_by_university(cls, university_id):
        """Get all variations for a university."""
        return cls.query.filter_by(university_id=university_id).all()
    
    @property
    def formatted_conditions(self):
        """Get conditions as a formatted list."""
        return [cond.strip() for cond in self.conditions] if self.conditions else []
    
    def has_requirement(self, key):
        """Check if a specific requirement exists."""
        return key in (self.requirements or {})

class InstitutionalRequirement(BaseModel):
    __tablename__ = 'institutional_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'))
    requirement_type = db.Column(db.String(100))
    requirements = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    university = db.relationship(
        'University', 
        backref=db.backref('institutional_requirements', lazy=True, cascade='all, delete-orphan')
    )
    
    __table_args__ = (
        db.Index('idx_institutional_req_university', 'university_id'),
    )
    def to_dict(self):
        """Convert requirement to dictionary format."""
        return {
            'id': self.id,
            'university_id': self.university_id,
            'requirement_type': self.requirement_type,
            'requirements': self.requirements,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_type(cls, requirement_type):
        """Get all requirements of a specific type."""
        return cls.query.filter_by(requirement_type=requirement_type).all()
    
class ExtendedSubjectRequirement(BaseModel):
    __tablename__ = 'extended_subject_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_requirement_id = db.Column(
        db.Integer, 
        db.ForeignKey('subject_requirement.id', ondelete='CASCADE'),
        unique=True
    )
    additional_requirements = db.Column(db.JSON)
    special_provisions = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    subject_requirement = db.relationship(
        'SubjectRequirement', 
        backref=db.backref(
            'extended_requirements',
            uselist=False,
            cascade='all, delete-orphan'
        )
    )
    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'subject_requirement_id': self.subject_requirement_id,
            'additional_requirements': self.additional_requirements,
            'special_provisions': self.special_provisions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def has_special_provisions(self):
        """Check if special provisions exist."""
        return bool(self.special_provisions)

class ExtendedProgramRequirement(BaseModel):
    __tablename__ = 'extended_program_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    course_requirement_id = db.Column(
        db.Integer, 
        db.ForeignKey('course_requirement.id', ondelete='CASCADE'),
        unique=True
    )
    specific_requirements = db.Column(db.JSON)
    additional_conditions = db.Column(db.ARRAY(db.Text))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    course_requirement = db.relationship(
        'CourseRequirement', 
        backref=db.backref(
            'extended_requirements',
            uselist=False,
            cascade='all, delete-orphan'
        )
    )
    
    __table_args__ = (
        db.Index('idx_extended_program_req', 'course_requirement_id'),
    )
    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'course_requirement_id': self.course_requirement_id,
            'specific_requirements': self.specific_requirements,
            'additional_conditions': self.additional_conditions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def formatted_conditions(self):
        """Get conditions as a formatted list."""
        return [cond.strip() for cond in self.additional_conditions] if self.additional_conditions else []

class DegreeAffiliation(BaseModel):
    __tablename__ = 'degree_affiliations'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'))
    affiliated_institution_abbrv = db.Column(db.String(255))
    affiliation_type = db.Column(db.String(100))
    program_offerings = db.Column(db.ARRAY(db.Text))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    parent_university = db.relationship(
        'University', 
        backref=db.backref('affiliations', lazy=True, cascade='all, delete-orphan')
    )
    
    __table_args__ = (
        db.UniqueConstraint('parent_university_id', 'affiliated_institution_abbrv'),
        db.Index('idx_degree_affiliations_parent', 'parent_university_id'),
        db.Index('idx_degree_affiliations_abbrv', 'affiliated_institution_abbrv'),
    )
    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'parent_university_id': self.parent_university_id,
            'affiliated_institution_abbrv': self.affiliated_institution_abbrv,
            'affiliation_type': self.affiliation_type,
            'program_offerings': self.program_offerings,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_affiliates(cls, university_id):
        """Get all affiliates for a university."""
        return cls.query.filter_by(parent_university_id=university_id).all()
    
    @property
    def formatted_offerings(self):
        """Get program offerings as a formatted list."""
        return [prog.strip() for prog in self.program_offerings] if self.program_offerings else []

class DistanceLearning(BaseModel):
    __tablename__ = 'distance_learning'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'))
    type = db.Column(db.Enum('elearning', 'sandwich', 'odl', name='distance_learning_type'), nullable=False)
    program_offerings = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    university = db.relationship(
        'University', 
        backref=db.backref('distance_learning_programs', lazy=True, cascade='all, delete-orphan')
    )
    
    __table_args__ = (
        db.UniqueConstraint('university_id', 'type'),
        db.Index('idx_distance_learning_university', 'university_id'),
    )

    @property
    def formatted_offerings(self):
        """Get formatted program offerings."""
        return self.program_offerings.split(',') if self.program_offerings else []
    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'university_id': self.university_id,
            'type': self.type.value if self.type else None,
            'program_offerings': self.formatted_offerings,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_type(cls, learning_type):
        """Get all programs of a specific type."""
        return cls.query.filter_by(type=learning_type).all()

class DistanceLearningRequirement(BaseModel):
    __tablename__ = 'distance_learning_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    institution_abbrv = db.Column(db.String(100))
    general_requirements = db.Column(db.JSON)
    special_program_requirements = db.Column(db.JSON)
    
    def __repr__(self):
        return f'<DistanceLearningRequirement {self.institution_abbrv}>'
    
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'institution_abbrv': self.institution_abbrv,
            'general_requirements': self.general_requirements,
            'special_program_requirements': self.special_program_requirements
        }
    
    @classmethod
    def get_by_institution(cls, institution_abbrv):
        """Get requirements for a specific institution."""
        return cls.query.filter_by(institution_abbrv=institution_abbrv).first()
    
    def has_special_requirements(self, program_type=None):
        """Check if special requirements exist for a program type."""
        if program_type:
            return program_type in (self.special_program_requirements or {})
        return bool(self.special_program_requirements)

class SpecializedProgramRequirement(BaseModel):
    __tablename__ = 'specialized_program_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    program_category = db.Column(db.String(100), nullable=False)
    general_requirements = db.Column(db.JSON)
    entry_requirements = db.Column(db.JSON)
    special_provisions = db.Column(db.JSON)
    search_vector = db.Column(TSVECTOR)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Course
    course = db.relationship(
        'Course',
        backref=db.backref('specialized_requirements', lazy=True, cascade='all, delete-orphan')
    )
    
    __table_args__ = (
        db.Index('idx_specialized_program_requirements_search', 'search_vector', postgresql_using='gin'),
        db.Index('idx_specialized_program_requirements_course', 'course_id'),
        db.UniqueConstraint('course_id', 'program_category', name='uq_course_program_category')
    )
    
    def __repr__(self):
        return f"<SpecializedProgramRequirement {self.program_category} for Course {self.course_id}>"
    
    def to_dict(self):
        """Convert the specialized program requirement to a dictionary format."""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'program_category': self.program_category,
            'general_requirements': self.general_requirements,
            'entry_requirements': self.entry_requirements,
            'special_provisions': self.special_provisions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_category(cls, program_category):
        """Get all requirements for a specific program category."""
        return cls.query.filter_by(program_category=program_category).all()
    
    @classmethod
    def get_by_course(cls, course_id):
        """Get all specialized requirements for a specific course."""
        return cls.query.filter_by(course_id=course_id).all()
    
    def has_special_provisions(self):
        """Check if special provisions exist for this program requirement."""
        return bool(self.special_provisions)

class SpecialInstitutionalRequirement(BaseModel):
    """Model for special institutional requirements specific to universities."""
    __tablename__ = 'special_institutional_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'), nullable=False)
    requirements = db.Column(db.JSON, nullable=False)
    special_notes = db.Column(db.ARRAY(db.Text))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    university = db.relationship(
        'University',
        back_populates='special_institutional_requirements',
        single_parent=True  # Add this flag since we have a unique constraint
    )
    
    __table_args__ = (
        db.Index('idx_special_req_university', 'university_id'),
        db.Index('idx_special_req_requirements', 'requirements', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f'<SpecialInstitutionalRequirement {self.id} for University {self.university_id}>'
    
    def to_dict(self):
        """Convert the requirement to a dictionary format."""
        return {
            'id': self.id,
            'university_id': self.university_id,
            'requirements': self.requirements,
            'special_notes': self.special_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_by_university(cls, university_id):
        """Get special requirements for a specific university."""
        try:
            return cls.query.filter_by(university_id=university_id).first()
        except Exception as e:
            logger.error(f"Error fetching special requirements for university {university_id}: {str(e)}")
            return None
    
    def has_requirement(self, key):
        """Check if a specific requirement exists."""
        try:
            return key in self.requirements if self.requirements else False
        except Exception as e:
            logger.error(f"Error checking requirement {key}: {str(e)}")
            return False
    
    def get_special_notes(self):
        """Get special notes as a formatted list."""
        return self.special_notes if self.special_notes else []
    
    @classmethod
    def search_by_requirement(cls, requirement_key):
        """Search for universities with a specific requirement."""
        try:
            return cls.query.filter(
                cls.requirements.has_key(requirement_key)  # Using JSONB containment
            ).all()
        except Exception as e:
            logger.error(f"Error searching requirements with key {requirement_key}: {str(e)}")
            return []

class TeachingRequirement(BaseModel):
    """Model for teaching subject requirements and combinations."""
    __tablename__ = 'teaching_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'))
    general_requirements = db.Column(db.JSON)
    acceptable_combinations = db.Column(db.ARRAY(db.Text))
    special_notes = db.Column(db.ARRAY(db.Text))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship(
        'Course',
        backref=db.backref('teaching_requirements', lazy=True, cascade='all, delete-orphan')
    )
    
    __table_args__ = (
        db.Index('idx_teaching_requirements_created_at', 'created_at'),
        db.UniqueConstraint('course_id', name='teaching_requirements_course_id_key')
    )
    
    def __repr__(self):
        return f'<TeachingRequirement {self.id} for Course {self.course_id}>'
    
    def to_dict(self):
        """Convert the teaching requirement to a dictionary format."""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'general_requirements': self.general_requirements,
            'acceptable_combinations': self.acceptable_combinations,
            'special_notes': self.special_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_course(cls, course_id):
        """Get teaching requirements for a specific course."""
        try:
            return cls.query.filter_by(course_id=course_id).first()
        except Exception as e:
            logger.error(f"Error fetching teaching requirements for course {course_id}: {str(e)}")
            return None
    
    def get_combinations(self):
        """Get acceptable subject combinations as a formatted list."""
        return self.acceptable_combinations if self.acceptable_combinations else []
    
    def get_special_notes(self):
        """Get special notes as a formatted list."""
        return self.special_notes if self.special_notes else []
    
    @classmethod
    def get_all_with_combinations(cls):
        """Get all teaching requirements that have specific subject combinations."""
        try:
            return cls.query.filter(
                cls.acceptable_combinations.isnot(None)
            ).all()
        except Exception as e:
            logger.error(f"Error fetching teaching requirements with combinations: {str(e)}")
            return []

class MilitaryRequirement(BaseModel):
    """Model for military institution requirements."""
    __tablename__ = 'military_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    institution_name = db.Column(db.String(255), unique=True)
    age_requirements = db.Column(db.JSON)
    physical_requirements = db.Column(db.JSON)
    additional_requirements = db.Column(db.ARRAY(db.Text))
    special_notes = db.Column(db.ARRAY(db.Text))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MilitaryRequirement {self.institution_name}>'

    def to_dict(self):
        """Convert the military requirement to a dictionary format."""
        return {
            'id': self.id,
            'institution_name': self.institution_name,
            'age_requirements': self.age_requirements,
            'physical_requirements': self.physical_requirements,
            'additional_requirements': self.additional_requirements,
            'special_notes': self.special_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_by_institution(cls, institution_name):
        """Get requirements for a specific military institution."""
        return cls.query.filter_by(institution_name=institution_name).first()

    def has_physical_requirements(self):
        """Check if physical requirements exist."""
        return bool(self.physical_requirements)

    def get_formatted_requirements(self):
        """Get all requirements in a formatted structure."""
        return {
            'age': self.age_requirements,
            'physical': self.physical_requirements,
            'additional': self.additional_requirements,
            'special_notes': self.special_notes
        }


class MilitaryDefenseRequirement(BaseModel):
    """Model for military and defense institution requirements."""
    __tablename__ = 'military_defense_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    institution_name = db.Column(db.String(100))
    age_requirements = db.Column(db.JSON)
    physical_requirements = db.Column(db.JSON)
    additional_requirements = db.Column(db.ARRAY(db.Text))
    special_notes = db.Column(db.ARRAY(db.Text))

    def __repr__(self):
        return f'<MilitaryDefenseRequirement {self.institution_name}>'

    def to_dict(self):
        """Convert the military defense requirement to a dictionary format."""
        return {
            'id': self.id,
            'institution_name': self.institution_name,
            'age_requirements': self.age_requirements,
            'physical_requirements': self.physical_requirements,
            'additional_requirements': self.additional_requirements,
            'special_notes': self.special_notes
        }

    @classmethod
    def get_by_institution(cls, institution_name):
        """Get requirements for a specific military/defense institution."""
        return cls.query.filter_by(institution_name=institution_name).first()

    def has_physical_requirements(self):
        """Check if physical requirements exist."""
        return bool(self.physical_requirements)

    def get_formatted_requirements(self):
        """Get all requirements in a formatted structure."""
        return {
            'age': self.age_requirements,
            'physical': self.physical_requirements,
            'additional': self.additional_requirements,
            'special_notes': self.special_notes
        }

class NABTEBAcceptance(BaseModel):
    """Model for NABTEB acceptance criteria by universities."""
    __tablename__ = 'nabteb_acceptance'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'))
    accepts_as_olevel = db.Column(db.Boolean, default=False)
    accepts_advanced_cert = db.Column(db.Boolean, default=False)
    verification_source = db.Column(db.String(255))
    special_conditions = db.Column(db.Text)
    verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    university = db.relationship(
        'University',
        backref=db.backref('nabteb_acceptance', lazy=True, cascade='all, delete-orphan')
    )
    faculty_acceptances = db.relationship(
        'NABTEBFacultyAcceptance',
        backref='nabteb_acceptance',
        lazy=True,
        cascade='all, delete-orphan'
    )
    program_acceptances = db.relationship(
        'NABTEBProgramAcceptance',
        backref='nabteb_acceptance',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<NABTEBAcceptance {self.university.name}>'

    def to_dict(self):
        """Convert the NABTEB acceptance criteria to a dictionary format."""
        return {
            'id': self.id,
            'university_id': self.university_id,
            'accepts_as_olevel': self.accepts_as_olevel,
            'accepts_advanced_cert': self.accepts_advanced_cert,
            'verification_source': self.verification_source,
            'special_conditions': self.special_conditions,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'faculties': [fa.to_dict() for fa in self.faculty_acceptances],
            'programs': [pa.to_dict() for pa in self.program_acceptances]
        }

    @classmethod
    def get_by_university(cls, university_id):
        """Get NABTEB acceptance criteria for a specific university."""
        return cls.query.filter_by(university_id=university_id).first()

    @classmethod
    def get_all_accepting_universities(cls):
        """Get all universities that accept NABTEB."""
        return cls.query.filter(
            (cls.accepts_as_olevel == True) | 
            (cls.accepts_advanced_cert == True)
        ).all()

    def accepts_faculty(self, faculty_name):
        """Check if a specific faculty accepts NABTEB."""
        return any(fa.faculty_name == faculty_name for fa in self.faculty_acceptances)

    def accepts_program(self, program_name):
        """Check if a specific program accepts NABTEB."""
        return any(pa.program_name == program_name for pa in self.program_acceptances)

class NABTEBFacultyAcceptance(BaseModel):
    """Model for faculty-level NABTEB acceptance criteria."""
    __tablename__ = 'nabteb_faculty_acceptance'
    
    id = db.Column(db.Integer, primary_key=True)
    nabteb_acceptance_id = db.Column(db.Integer, db.ForeignKey('nabteb_acceptance.id', ondelete='CASCADE'))
    faculty_name = db.Column(db.String(255), nullable=False)
    acceptance_type = db.Column(db.Enum('full', 'partial', 'conditional', name='faculty_acceptance_type'))
    conditions = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'faculty_name': self.faculty_name,
            'acceptance_type': self.acceptance_type,
            'conditions': self.conditions
        }

class NABTEBProgramAcceptance(BaseModel):
    """Model for program-level NABTEB acceptance criteria."""
    __tablename__ = 'nabteb_program_acceptance'
    
    id = db.Column(db.Integer, primary_key=True)
    nabteb_acceptance_id = db.Column(db.Integer, db.ForeignKey('nabteb_acceptance.id', ondelete='CASCADE'))
    program_name = db.Column(db.String(255), nullable=False)
    acceptance_type = db.Column(db.Enum('full', 'partial', 'conditional', name='program_acceptance_type'))
    conditions = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'program_name': self.program_name,
            'acceptance_type': self.acceptance_type,
            'conditions': self.conditions
        }

class ProfessionalCourseRequirement(BaseModel):
    """Model for professional course requirements."""
    __tablename__ = 'professional_course_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False, unique=True)
    o_level_requirements = db.Column(db.JSON)
    utme_requirements = db.Column(db.JSON)
    direct_entry_requirements = db.Column(db.JSON)
    special_conditions = db.Column(db.Text)
    search_vector = db.Column(TSVECTOR)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    course = db.relationship(
        'Course',
        backref=db.backref('professional_requirements', lazy=True, cascade='all, delete-orphan')
    )
    
    specializations = db.relationship(
        'ProfessionalCourseSpecialization',
        back_populates='professional_requirement',
        lazy=True,
        cascade='all, delete-orphan'
    )
    
    __table_args__ = (
        db.Index('idx_prof_course_req_search', 'search_vector', postgresql_using='gin'),
        db.Index('idx_prof_course_req_course', 'course_id'),
    )
    
    def __repr__(self):
        return f'<ProfessionalCourseRequirement {self.course_id}>'
    
    def to_dict(self):
        """Convert the professional course requirement to a dictionary format."""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'o_level_requirements': self.o_level_requirements,
            'utme_requirements': self.utme_requirements,
            'direct_entry_requirements': self.direct_entry_requirements,
            'special_conditions': self.special_conditions,
            'specializations': [s.to_dict() for s in self.specializations],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_course(cls, course_id):
        """Get professional requirements for a specific course."""
        return cls.query.filter_by(course_id=course_id).first()
    
    @classmethod
    def get_all_with_specializations(cls):
        """Get all professional requirements that have specializations."""
        return cls.query.join(ProfessionalCourseSpecialization).all()

class ProfessionalCourseSpecialization(BaseModel):
    """Model for professional course specializations."""
    __tablename__ = 'professional_course_specializations'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    professional_requirement_id = db.Column(db.Integer, db.ForeignKey('professional_course_requirements.id', ondelete='CASCADE'), nullable=False)
    specialization_name = db.Column(db.String(255), nullable=False)
    requirements = db.Column(db.JSON)
    normalized_name = db.Column(db.String(255))
    search_vector = db.Column(TSVECTOR)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    course = db.relationship(
        'Course',
        backref=db.backref('specializations', lazy=True, cascade='all, delete-orphan')
    )
    
    professional_requirement = db.relationship(
        'ProfessionalCourseRequirement',
        back_populates='specializations'
    )
    
    __table_args__ = (
        db.Index('idx_prof_course_spec_search', 'search_vector', postgresql_using='gin'),
        db.Index('idx_prof_course_spec_course', 'course_id'),
        db.Index('idx_prof_course_spec_prof_req', 'professional_requirement_id'),
        db.Index('idx_prof_course_spec_norm_name', 'normalized_name'),
        db.UniqueConstraint('course_id', 'specialization_name', name='uq_course_specialization')
    )
    
    def __repr__(self):
        return f'<ProfessionalCourseSpecialization {self.specialization_name}>'
    
    def to_dict(self):
        """Convert the specialization to a dictionary format."""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'specialization_name': self.specialization_name,
            'requirements': self.requirements,
            'normalized_name': self.normalized_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_course(cls, course_id):
        """Get all specializations for a specific course."""
        return cls.query.filter_by(course_id=course_id).all()
    
    @classmethod
    def get_by_normalized_name(cls, normalized_name):
        """Get specializations by normalized name."""
        return cls.query.filter_by(normalized_name=normalized_name).all()

class ReligiousInstitutionRequirement(BaseModel):
    """Model for religious institution requirements."""
    __tablename__ = 'religious_institution_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'), unique=True)
    entry_requirements = db.Column(db.JSON)
    special_provisions = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    university = db.relationship(
        'University',
        backref=db.backref('religious_requirements', lazy=True, cascade='all, delete-orphan')
    )
    
    def __repr__(self):
        return f'<ReligiousInstitutionRequirement {self.university_id}>'
    
    def to_dict(self):
        """Convert the religious institution requirement to a dictionary format."""
        return {
            'id': self.id,
            'university_id': self.university_id,
            'entry_requirements': self.entry_requirements,
            'special_provisions': self.special_provisions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_by_university(cls, university_id):
        """Get religious institution requirements for a specific university."""
        return cls.query.filter_by(university_id=university_id).first()

class SandwichProgramRequirement(BaseModel):
    """Model for sandwich program requirements."""
    __tablename__ = 'sandwich_program_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    target_audience = db.Column(db.Text)
    entry_requirements = db.Column(db.Text)
    special_conditions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_sandwich_req_target', 'target_audience'),
    )
    
    def __repr__(self):
        return f'<SandwichProgramRequirement {self.target_audience}>'
    
    def to_dict(self):
        """Convert the sandwich program requirement to a dictionary format."""
        return {
            'id': self.id,
            'target_audience': self.target_audience,
            'entry_requirements': self.entry_requirements,
            'special_conditions': self.special_conditions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_by_target_audience(cls, target_audience):
        """Get requirements for a specific target audience."""
        try:
            return cls.query.filter_by(target_audience=target_audience).first()
        except Exception as e:
            logger.error(f"Error getting sandwich program requirements: {str(e)}")
            return None
    
    @classmethod
    def get_all_requirements(cls):
        """Get all sandwich program requirements."""
        try:
            return cls.query.all()
        except Exception as e:
            logger.error(f"Error getting all sandwich program requirements: {str(e)}")
            return []