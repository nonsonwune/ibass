# app/utils/search.py

from ..extensions import db, cache
from ..models.university import University, Course, CourseRequirement, State, ProgrammeType
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
import time
import psycopg2.extras

def verify_search_vector_integrity():
    """Verify search vector data integrity"""
    try:
        # Check for any null search vectors
        uni_nulls = db.session.scalar(
            text("SELECT COUNT(*) FROM university WHERE search_vector IS NULL")
        )
        course_nulls = db.session.scalar(
            text("SELECT COUNT(*) FROM course WHERE search_vector IS NULL")
        )
        
        if uni_nulls > 0:
            current_app.logger.warning(
                f"Found {uni_nulls} universities with null search vectors"
            )
        if course_nulls > 0:
            current_app.logger.warning(
                f"Found {course_nulls} courses with null search vectors"
            )
            
        return uni_nulls == 0 and course_nulls == 0
        
    except Exception as e:
        current_app.logger.error(f"Error verifying search vector integrity: {str(e)}")
        return False

def repair_search_vectors():
    """Repair any null or invalid search vectors"""
    try:
        # Update any null university vectors using the new schema
        result = db.session.execute(text("""
            UPDATE university u
            SET search_vector = to_tsvector('english', 
                COALESCE(u.university_name, '') || ' ' ||
                COALESCE(s.name, '') || ' ' ||
                COALESCE(pt.name, '')
            )
            FROM state s, programme_type pt
            WHERE u.state_id = s.id 
            AND u.programme_type_id = pt.id
            AND u.search_vector IS NULL
        """))
        fixed_unis = result.rowcount
        
        # Update any null course vectors
        result = db.session.execute(text("""
            UPDATE course
            SET search_vector = to_tsvector('english',
                COALESCE(course_name, '') || ' ' ||
                COALESCE(code, '')
            )
            WHERE search_vector IS NULL
        """))
        fixed_courses = result.rowcount
        
        db.session.commit()
        
        if fixed_unis > 0 or fixed_courses > 0:
            current_app.logger.info(
                f"Repaired {fixed_unis} university and {fixed_courses} course search vectors"
            )
        
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error repairing search vectors: {str(e)}")
        return False

def init_search_vectors():
    """Initialize search vectors for universities and courses"""
    try:
        # Initialize university search vectors
        university_sql = """
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
        db.session.execute(text(university_sql))
        
        # Initialize course search vectors
        course_sql = """
            UPDATE course
            SET search_vector = to_tsvector('english',
                COALESCE(course_name, '') || ' ' ||
                COALESCE(code, '')
            )
        """
        db.session.execute(text(course_sql))
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error initializing search vectors: {str(e)}")
        return False

def perform_search(query_text, state=None, program_type=None, page=1, per_page=10):
    """Unified search function with caching and optimized queries"""
    cache_key = f'search:{query_text}:{state}:{program_type}:{page}'
    results = cache.get(cache_key)
    
    if results is None:
        try:
            # Calculate pagination
            offset = (page - 1) * per_page
            
            # Enhanced university query with better join handling
            universities = execute_university_search(
                query_text, state, program_type, per_page, offset
            )
            total_unis = get_university_count(query_text, state, program_type)
            
            # Enhanced course query with better join handling
            courses = execute_course_search(
                query_text, state, program_type, per_page, offset
            )
            total_courses = get_course_count(query_text, state, program_type)
            
            # Create paginated results with properly mapped fields
            results = {
                'universities': {
                    'items': [{
                        'id': uni['id'],
                        'university_name': uni['university_name'],
                        'state': uni['state_name'],  # Map from the query result
                        'program_type': uni['program_type_name']  # Map from the query result
                    } for uni in universities],
                    'total': total_unis,
                    'has_next': offset + per_page < total_unis,
                    'has_prev': page > 1,
                    'page': page
                },
                'courses': {
                    'items': courses,
                    'total': total_courses,
                    'has_next': offset + per_page < total_courses,
                    'has_prev': page > 1,
                    'page': page
                }
            }
            
            cache.set(cache_key, results, timeout=300)  # Cache for 5 minutes
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Search error: {str(e)}")
            raise
            
    return results

def execute_university_search(query_text, state, program_type, limit, offset):
    """Execute university search query"""
    query = text("""
        SELECT 
            u.id,
            u.university_name,
            s.name as state_name,
            pt.name as program_type_name
        FROM university u
        LEFT JOIN state s ON u.state_id = s.id
        LEFT JOIN programme_type pt ON u.programme_type_id = pt.id
        WHERE (:state IS NULL OR s.name = :state)
        AND (:program_type IS NULL OR pt.name = :program_type)
        AND (
            :query IS NULL 
            OR u.search_vector @@ plainto_tsquery('english', :query)
            OR u.university_name ILIKE :like_query
        )
        ORDER BY u.university_name
        LIMIT :limit OFFSET :offset
    """)
    
    return db.session.execute(
        query,
        {
            'state': state,
            'program_type': program_type,
            'query': query_text,
            'like_query': f'%{query_text}%' if query_text else None,
            'limit': limit,
            'offset': offset
        }
    ).mappings().all()

def get_university_count(query_text, state, program_type):
    """Get total count of matching universities"""
    query = text("""
        SELECT COUNT(*)
        FROM university u
        JOIN state s ON u.state_id = s.id
        JOIN programme_type pt ON u.programme_type_id = pt.id
        WHERE (:state IS NULL OR s.name = :state)
        AND (:program_type IS NULL OR pt.name = :program_type)
        AND (
            :query IS NULL 
            OR u.search_vector @@ plainto_tsquery('english', :query)
            OR u.university_name ILIKE :like_query
        )
    """)
    
    return db.session.scalar(
        query,
        {
            'state': state,
            'program_type': program_type,
            'query': query_text,
            'like_query': f'%{query_text}%' if query_text else None
        }
    )

def execute_course_search(query_text, state, program_type, limit, offset):
    """Execute course search query"""
    query = text("""
        WITH filtered_courses AS (
            SELECT 
                c.id,
                c.course_name,
                c.code,
                s.name as state,
                pt.name as program_type,
                cr.utme_requirements,
                cr.direct_entry_requirements,
                sr.subjects
            FROM course c
            JOIN course_requirement cr ON c.id = cr.course_id
            JOIN university u ON cr.university_id = u.id
            JOIN state s ON u.state_id = s.id
            JOIN programme_type pt ON u.programme_type_id = pt.id
            LEFT JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
            WHERE (:state IS NULL OR s.name = :state)
            AND (:program_type IS NULL OR pt.name = :program_type)
            AND (
                :query IS NULL 
                OR c.search_vector @@ plainto_tsquery('english', :query)
                OR c.course_name ILIKE :like_query
                OR c.code ILIKE :like_query
            )
        )
        SELECT *
        FROM filtered_courses
        ORDER BY course_name
        LIMIT :limit OFFSET :offset
    """)
    
    return db.session.execute(
        query,
        {
            'state': state,
            'program_type': program_type,
            'query': query_text,
            'like_query': f'%{query_text}%' if query_text else None,
            'limit': limit,
            'offset': offset
        }
    ).mappings().all()

def get_course_count(query_text, state, program_type):
    """Get total count of matching courses"""
    query = text("""
        SELECT COUNT(*)
        FROM course c
        JOIN course_requirement cr ON c.id = cr.course_id
        JOIN university u ON cr.university_id = u.id
        JOIN state s ON u.state_id = s.id
        JOIN programme_type pt ON u.programme_type_id = pt.id
        WHERE (:state IS NULL OR s.name = :state)
        AND (:program_type IS NULL OR pt.name = :program_type)
        AND (
            :query IS NULL 
            OR c.search_vector @@ plainto_tsquery('english', :query)
            OR c.course_name ILIKE :like_query
            OR c.code ILIKE :like_query
        )
    """)
    
    return db.session.scalar(
        query,
        {
            'state': state,
            'program_type': program_type,
            'query': query_text,
            'like_query': f'%{query_text}%' if query_text else None
        }
    )