# app/models/requirement.py
from ..extensions import db
from .base import BaseModel
from sqlalchemy import exc
from contextlib import contextmanager
import logging

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
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    utme_template_id = db.Column(db.Integer, db.ForeignKey('utme_requirement_template.id'))
    de_template_id = db.Column(db.Integer, db.ForeignKey('direct_entry_requirement_template.id'))
    
    university = db.relationship('University', back_populates='course_requirements')
    course = db.relationship('Course', back_populates='requirements')
    subject_requirement = db.relationship(
        'SubjectRequirement', 
        back_populates='requirement',
        uselist=False,
        cascade='all, delete-orphan',
        single_parent=True 
    )
    utme_template = db.relationship('UTMERequirementTemplate', back_populates='course_requirements')
    de_template = db.relationship('DirectEntryRequirementTemplate', back_populates='course_requirements')
    
    __table_args__ = (
        db.Index('idx_course_requirement_composite', 'course_id', 'university_id'),
        db.Index('idx_course_requirement_course_id', 'course_id'),
        db.Index('idx_course_requirement_template_ids', 'utme_template_id', 'de_template_id'),
    )

    @property
    def utme_requirements(self):
        return self.utme_template.requirements if self.utme_template else None

    @property
    def direct_entry_requirements(self):
        return self.de_template.requirements if self.de_template else None

    @classmethod
    def copy_course_requirements(cls, source_course_id, target_course_id):
        """
        Copy course requirements from source course to target course.
        
        Args:
            source_course_id (int): ID of the source course
            target_course_id (int): ID of the target course
            
        Returns:
            tuple: (bool, str) - (Success status, message)
        """
        try:
            # Validate course IDs
            from .university import Course  # Import here to avoid circular imports
            source_course = Course.query.get(source_course_id)
            target_course = Course.query.get(target_course_id)
            
            if not source_course or not target_course:
                return False, "Invalid course ID(s)"
            
            if source_course_id == target_course_id:
                return False, "Source and target courses cannot be the same"
                
            with session_scope() as session:
                # Get all requirements for source course
                source_requirements = cls.query.filter_by(
                    course_id=source_course_id
                ).all()
                
                if not source_requirements:
                    return False, "No requirements found for source course"
                
                # Delete existing requirements for target course
                cls.query.filter_by(course_id=target_course_id).delete()
                
                # Copy requirements to target course
                for req in source_requirements:
                    new_req = cls(
                        course_id=target_course_id,
                        university_id=req.university_id,
                        utme_template_id=req.utme_template_id,
                        de_template_id=req.de_template_id
                    )
                    session.add(new_req)
                    
                    # Copy subject requirements if they exist
                    if req.subject_requirement:
                        new_subject_req = SubjectRequirement(
                            subjects=req.subject_requirement.subjects
                        )
                        new_req.subject_requirement = new_subject_req
                
                logger.info(f"Successfully copied requirements from course {source_course_id} to {target_course_id}")
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
    
