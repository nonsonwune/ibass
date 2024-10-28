# app/models/university.py
from ..extensions import db, cache
from .base import BaseModel
from sqlalchemy import Index, func, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import expression
import re

class University(BaseModel):
    __tablename__ = 'university'
    
    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(256), unique=True, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    program_type = db.Column(db.String(50), nullable=False)
    website = db.Column(db.String(255))
    established = db.Column(db.Integer)
    
    # Add search optimization fields
    search_vector = db.Column(TSVECTOR)
    
    # Add indexes
    __table_args__ = (
        Index('idx_university_name', 'university_name'),
        Index('idx_university_state', 'state'),
        Index('idx_university_program_type', 'program_type'),
        Index('idx_university_search', 'search_vector', postgresql_using='gin'),
    )
    
    # Update relationship to use proper backref
    courses = db.relationship(
        'Course', 
        backref=db.backref('university', lazy='joined'),
        lazy='select',
        primaryjoin="University.university_name == Course.university_name",
        cascade='all, delete-orphan'
    )
    
    @classmethod
    def search(cls, query_text, state=None, program_type=None):
        """Enhanced search method with proper query handling"""
        search_query = cls.query
        
        if query_text:
            # Clean and prepare search text
            clean_query = re.sub(r'[^\w\s]', '', query_text.lower())
            search_terms = clean_query.split()
            
            try:
                conditions = []
                for term in search_terms:
                    conditions.append(
                        text("search_vector @@ to_tsquery('english', :term)")
                        .bindparams(term=term)
                    )
                search_query = search_query.filter(or_(*conditions))
            except Exception as e:
                current_app.logger.error(f"Full-text search error: {str(e)}")
                # Fallback to ILIKE search
                search_query = search_query.filter(cls.university_name.ilike(f"%{query_text}%"))
        
        # Apply filters
        if state:
            search_query = search_query.filter(cls.state == state)
        if program_type:
            search_query = search_query.filter(cls.program_type == program_type)
            
        return search_query.order_by(cls.university_name)

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
            cache.set(cache_key, states, timeout=3600)  # Cache for 1 hour
            
        return states

class Course(BaseModel):
    __tablename__ = 'course'
    
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(256), nullable=False)
    university_name = db.Column(db.String(256), db.ForeignKey('university.university_name'), nullable=False)
    abbrv = db.Column(db.Text)
    direct_entry_requirements = db.Column(db.Text)
    utme_requirements = db.Column(db.Text)
    subjects = db.Column(db.Text)
    
    # Add search optimization fields
    search_vector = db.Column(TSVECTOR)
    
    # Add indexes
    __table_args__ = (
        Index('idx_course_name', 'course_name'),
        Index('idx_course_university', 'university_name'),
        Index('idx_course_search', 'search_vector', postgresql_using='gin'),
    )
    
@classmethod
def search(cls, query_text, university_name=None, program_type=None):
    """Enhanced course search method"""
    search_query = cls.query.join(University)
    
    if query_text:
        # Clean and prepare search text
        clean_query = re.sub(r'[^\w\s]', '', query_text.lower())
        search_terms = clean_query.split()
        
        try:
            conditions = []
            for term in search_terms:
                conditions.append(
                    text("search_vector @@ to_tsquery('english', :term)")
                    .bindparams(term=term)
                )
            search_query = search_query.filter(or_(*conditions))
        except Exception as e:
            current_app.logger.error(f"Full-text search error: {str(e)}")
            # Fallback to ILIKE search
            search_query = search_query.filter(or_(
                cls.course_name.ilike(f"%{query_text}%"),
                cls.abbrv.ilike(f"%{query_text}%")
            ))
    
    # Apply filters
    if university_name:
        search_query = search_query.filter(cls.university_name == university_name)
    if program_type:
        search_query = search_query.filter(University.program_type == program_type)
        
    return search_query.order_by(cls.course_name)