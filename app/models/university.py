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
    abbrv = db.Column(db.String(255))
    search_vector = db.Column(TSVECTOR)
    
    __table_args__ = (
        Index('idx_university_name', 'university_name'),
        Index('idx_university_state', 'state'),
        Index('idx_university_program_type', 'program_type'),
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
    def search(cls, query_text, state=None, program_type=None):
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
        
        if state:
            search_query = search_query.filter(cls.state == state)
        if program_type:
            search_query = search_query.filter(cls.program_type == program_type)
            
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
    def search(cls, query_text, university_id=None, program_type=None):
        """Enhanced course search method"""
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
                search_query = search_query.filter(db.or_(
                    cls.course_name.ilike(f"%{query_text}%"),
                    cls.code.ilike(f"%{query_text}%")
                ))
        
        if university_id or program_type:
            search_query = search_query.join(
                CourseRequirement,
                CourseRequirement.course_id == cls.id
            ).join(
                University,
                University.id == CourseRequirement.university_id
            )
            
            if university_id:
                search_query = search_query.filter(University.id == university_id)
            if program_type:
                search_query = search_query.filter(University.program_type == program_type)
                
        return search_query.distinct().order_by(cls.course_name)

class CourseRequirement(BaseModel):
    __tablename__ = 'course_requirement'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    utme_requirements = db.Column(db.Text)
    direct_entry_requirements = db.Column(db.Text)
    
    university = db.relationship('University', back_populates='course_requirements')
    course = db.relationship('Course', back_populates='requirements')
    subject_requirement = db.relationship(
        'SubjectRequirement', 
        back_populates='requirement',
        uselist=False,
        cascade='all, delete-orphan'
    )
    
    __table_args__ = (
        Index('idx_course_requirement_composite', 'course_id', 'university_id'),
        Index('idx_course_requirement_course_id', 'course_id'),
    )

class SubjectRequirement(BaseModel):
    __tablename__ = 'subject_requirement'
    
    id = db.Column(db.Integer, primary_key=True)
    course_requirement_id = db.Column(db.Integer, 
                                    db.ForeignKey('course_requirement.id'),
                                    nullable=False)
    subjects = db.Column(db.Text)
    
    requirement = db.relationship('CourseRequirement', back_populates='subject_requirement')