# app/models/university.py
from ..extensions import db, cache
from .base import BaseModel
from sqlalchemy import Index, func, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import expression
import re
from .requirement import CourseRequirement

# Define State model first
class State(BaseModel):
    __tablename__ = 'state'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    code = db.Column(db.String(2))
    region = db.Column(db.String(20))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    
    # Define relationship with back_populates
    universities = db.relationship('University', back_populates='state_info')
    
    def __repr__(self):
        return f"<State {self.name}>"
    
    @property
    def safe_name(self):
        return self.name if self.name else ""

# Define ProgrammeType model second
class ProgrammeType(BaseModel):
    __tablename__ = 'programme_type'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50))
    institution_type = db.Column(db.String(50))  # Added this column
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    
    # Define relationship with back_populates
    universities = db.relationship('University', back_populates='programme_type_info')
    
    def __repr__(self):
        return f"<ProgrammeType {self.name}>"

# Then define University model
class University(BaseModel):
    __tablename__ = 'university'
    
    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(200), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('state.id'))
    programme_type_id = db.Column(db.Integer, db.ForeignKey('programme_type.id'))
    website = db.Column(db.String(255))
    established = db.Column(db.Integer)
    abbrv = db.Column(db.String(255))  # Added this column to match database schema
    search_vector = db.Column(TSVECTOR)
    
    # Update relationships to use back_populates instead of backref
    state_info = db.relationship('State', back_populates='universities', lazy='joined')
    programme_type_info = db.relationship('ProgrammeType', back_populates='universities', lazy='joined')
    
    # Add search vector column
    search_vector = db.Column(TSVECTOR)

    # Single __table_args__ definition with valid indexes
    __table_args__ = (
        Index('idx_university_name', 'university_name'),
        Index('idx_university_search', 'search_vector', postgresql_using='gin'),
    )
    
    @property
    def state_name(self):
        """Get state name through relationship"""
        return self.state_info.name if self.state_info else None

    @property
    def programme_type_name(self):
        """Get programme type name through relationship"""
        return self.programme_type_info.name if self.programme_type_info else None

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
    
    @classmethod
    def get_all_states(cls):
        """Get all states with caching"""
        cache_key = 'all_states'
        states = cache.get(cache_key)
        
        if states is None:
            states = [state.name for state in 
                     db.session.query(State.name)
                     .order_by(State.name)
                     .all()]
            cache.set(cache_key, states, timeout=3600)
            
        return states

    # Update the course_requirements relationship with overlaps
    course_requirements = db.relationship(
        'CourseRequirement',
        back_populates='university',
        cascade='all, delete-orphan',
        overlaps="courses"
    )
    
    # Update courses relationship with viewonly and overlaps
    courses = db.relationship(
        'Course',
        secondary='course_requirement',
        primaryjoin="University.id == CourseRequirement.university_id",
        secondaryjoin="CourseRequirement.course_id == Course.id",
        backref=db.backref('universities', lazy='dynamic'),
        viewonly=True,  # Make it read-only
        overlaps="course_requirements,university"
    )

    @classmethod
    def initialize_search_vectors(cls):
        """Initialize search vectors with joined data"""
        sql = """
            WITH university_data AS (
                SELECT 
                    u.id,
                    COALESCE(u.university_name, '') || ' ' ||
                    COALESCE(s.name, '') || ' ' ||
                    COALESCE(pt.name, '') as combined_text
                FROM university u
                LEFT JOIN state s ON u.state_id = s.id
                LEFT JOIN programme_type pt ON u.programme_type_id = pt.id
            )
            UPDATE university u
            SET search_vector = to_tsvector('english', ud.combined_text)
            FROM university_data ud
            WHERE u.id = ud.id
        """
        return sql

# Then define Course model
class Course(BaseModel):
    __tablename__ = 'course'
    
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50))
    search_vector = db.Column(TSVECTOR)
    normalized_name = db.Column(db.String(255))
    
    # Update requirements relationship with overlaps
    requirements = db.relationship(
        'CourseRequirement',
        back_populates='course',
        lazy=True,
        overlaps="courses,universities"
    )
    
    __table_args__ = (
        db.UniqueConstraint('course_name', name='unique_course_name'),
        db.Index('idx_course_normalized_name', 'normalized_name'),
        db.Index('idx_course_search', 'search_vector', postgresql_using='gin')
    )

    @classmethod
    def search(cls, query_text=None, university_id=None, programme_type_id=None):
        """Optimized course search method"""
        base_query = db.session.query(
            cls.id,
            cls.course_name,
            cls.code,
            ProgrammeType.name.label('programme_type'),
            University.university_name
        ).select_from(cls)
        
        base_query = base_query.join(
            CourseRequirement,
            CourseRequirement.course_id == cls.id
        ).join(
            University,
            University.id == CourseRequirement.university_id
        ).join(
            ProgrammeType,
            ProgrammeType.id == University.programme_type_id
        )
        
        if query_text:
            clean_query = re.sub(r'[^\w\s]', '', query_text.lower())
            search_terms = clean_query.split()
            
            try:
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
            
        if programme_type_id:
            base_query = base_query.filter(University.programme_type_id == programme_type_id)
        
        return base_query.distinct().order_by(cls.course_name)