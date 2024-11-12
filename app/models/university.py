# app/models/university.py
from ..extensions import db, cache
from .base import BaseModel
from sqlalchemy import Index, func, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import expression
import re
from .requirement import CourseRequirement

class University(BaseModel):
    __tablename__ = 'university'
    
    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(256), unique=True, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    program_type = db.Column(db.String(50), nullable=False)
    website = db.Column(db.String(255))
    established = db.Column(db.Integer)
    abbrv = db.Column(db.String(255))
    search_vector = db.Column(TSVECTOR)
    state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
    programme_type_id = db.Column(db.Integer, db.ForeignKey('programme_type.id'), nullable=False)
    
    # Add relationships for new foreign keys
    state_info = db.relationship('State', backref='universities')
    programme_type_info = db.relationship('ProgrammeType', backref='universities')
    
    __table_args__ = (
        Index('idx_university_name', 'university_name'),
        Index('idx_university_program_type_hash', 'program_type', postgresql_using='hash'),
        Index('idx_university_search', 'search_vector', postgresql_using='gin'),
    )
    
    courses = db.relationship(
        'Course',
        secondary='course_requirement',
        primaryjoin="University.id == CourseRequirement.university_id",
        secondaryjoin="CourseRequirement.course_id == Course.id",
        back_populates='universities',
        viewonly=True
    )
    
    course_requirements = db.relationship(
        'CourseRequirement',
        back_populates='university',
        cascade='all, delete-orphan'
    )

    @classmethod
    def search(cls, query_text=None, state_id=None, programme_type_id=None):
        """Enhanced search method with proper query handling"""
        search_query = cls.query
        
        if query_text:
            clean_query = re.sub(r'[^\w\s]', '', query_text.lower())
            search_terms = clean_query.split()
            
            try:
                conditions = []
                for term in search_terms:
                    conditions.append(
                        text("search_vector @@ to_tsquery('english', :term)")
                        .bindparams(term=term + ':*')
                    )
                search_query = search_query.filter(db.or_(*conditions))
            except Exception as e:
                search_query = search_query.filter(cls.university_name.ilike(f"%{query_text}%"))
        
        if state_id:
            search_query = search_query.filter(cls.state_id == state_id)
        if programme_type_id:
            search_query = search_query.filter(cls.programme_type_id == programme_type_id)
            
        return search_query.order_by(cls.university_name)
    
    __table_args__ = (
        Index('idx_university_filters', 'state', 'program_type'),
        Index('idx_university_name', 'university_name'),
        Index('idx_university_program_type', 'program_type'),
        Index('idx_university_search', 'search_vector', postgresql_using='gin'),
    )

    @classmethod
    def get_all_states(cls):
        """Get all states with caching"""
        cache_key = 'all_states'
        states = cache.get(cache_key)
        
        if states is None:
            states = [state[0] for state in 
                     db.session.query(cls.state)
                     .distinct()
                     .order_by(cls.state)
                     .all()]
            cache.set(cache_key, states, timeout=3600)
            
        return states

    @property
    def state_name(self):
        """Compatibility property for existing views"""
        return self.state_info.name if self.state_info else self.state

    @property
    def programme_type_name(self):
        """Compatibility property for existing views"""
        return self.programme_type_info.name if self.programme_type_info else self.program_type

class Course(BaseModel):
    __tablename__ = 'course'
    
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(256), unique=True, nullable=False)
    code = db.Column(db.String(50))
    search_vector = db.Column(TSVECTOR)
    
    __table_args__ = (
        Index('idx_course_name', 'course_name'),
        Index('idx_course_search', 'search_vector', postgresql_using='gin'),
    )
    
    universities = db.relationship(
        'University',
        secondary='course_requirement',
        primaryjoin="Course.id == CourseRequirement.course_id",
        secondaryjoin="CourseRequirement.university_id == University.id",
        back_populates='courses',
        viewonly=True
    )
    
    requirements = db.relationship(
        'CourseRequirement',
        back_populates='course',
        cascade='all, delete-orphan',
        lazy='joined'
    )

    @classmethod
    def search(cls, query_text=None, university_id=None, program_type=None):
        """Optimized course search method"""
        # Start with a base query
        base_query = db.session.query(
            cls.id,
            cls.course_name,
            cls.code,
            University.program_type,
            University.university_name
        ).select_from(cls)
        
        # Use join instead of subquery for better performance
        base_query = base_query.join(
            CourseRequirement,
            CourseRequirement.course_id == cls.id
        ).join(
            University,
            University.id == CourseRequirement.university_id
        )
        
        if query_text:
            clean_query = re.sub(r'[^\w\s]', '', query_text.lower())
            search_terms = clean_query.split()
            
            try:
                # Use GIN index for full-text search
                combined_terms = ' & '.join(f"{term}:*" for term in search_terms)
                base_query = base_query.filter(
                    text("course.search_vector @@ to_tsquery('english', :terms)")
                    .bindparams(terms=combined_terms)
                )
            except Exception:
                base_query = base_query.filter(db.or_(
                    cls.course_name.ilike(f"%{query_text}%"),
                    cls.code.ilike(f"%{query_text}%")
                ))
        
        if university_id:
            base_query = base_query.filter(University.id == university_id)
            
        if program_type:
            if isinstance(program_type, (list, tuple)):
                base_query = base_query.filter(University.program_type.in_(program_type))
            else:
                base_query = base_query.filter(University.program_type == program_type)
        
        # Add pagination
        base_query = base_query.distinct().order_by(cls.course_name)
        
        return base_query

# Add new models for state and programme_type
class State(BaseModel):
    __tablename__ = 'state'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

class ProgrammeType(BaseModel):
    __tablename__ = 'programme_type'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())