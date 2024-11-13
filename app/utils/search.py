# app/utils/search.py
from ..extensions import db, cache
from ..models.university import University, Course
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
    """Initialize search vectors for universities"""
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
    return db.session.execute(text(sql))

def perform_search(query_text, state=None, program_type=None, page=1, per_page=10):
    """Unified search function with caching and optimized queries"""
    cache_key = f'search:{query_text}:{state}:{program_type}:{page}'
    results = cache.get(cache_key)
    
    if results is None:
        try:
            # Use materialized query for better performance
            base_university_query = text("""
                WITH filtered_universities AS (
                    SELECT *
                    FROM university
                    WHERE (:state IS NULL OR state = :state)
                    AND (:program_type IS NULL OR program_type = :program_type)
                    AND (
                        :query IS NULL 
                        OR search_vector @@ plainto_tsquery('english', :query)
                        OR university_name ILIKE :like_query
                    )
                )
                SELECT *
                FROM filtered_universities
                ORDER BY university_name
                LIMIT :limit OFFSET :offset
            """)
            
            # Calculate pagination
            offset = (page - 1) * per_page
            
            # Execute university query with fallback to ILIKE
            universities = db.session.execute(
                base_university_query,
                {
                    'state': state,
                    'program_type': program_type,
                    'query': query_text,
                    'like_query': f'%{query_text}%' if query_text else None,
                    'limit': per_page,
                    'offset': offset
                }
            ).mappings().all()
            
            # Get total count
            total_unis = db.session.scalar(
                text("""
                    SELECT COUNT(*)
                    FROM university
                    WHERE (:state IS NULL OR state = :state)
                    AND (:program_type IS NULL OR program_type = :program_type)
                    AND (
                        :query IS NULL 
                        OR search_vector @@ plainto_tsquery('english', :query)
                        OR university_name ILIKE :like_query
                    )
                """),
                {
                    'state': state,
                    'program_type': program_type,
                    'query': query_text,
                    'like_query': f'%{query_text}%' if query_text else None
                }
            )
            
            # Similar optimization for courses with JOIN
            base_course_query = text("""
                WITH filtered_courses AS (
                    SELECT 
                        c.*,
                        u.state,
                        u.program_type,
                        cr.utme_requirements,
                        cr.direct_entry_requirements,
                        sr.subjects
                    FROM course c
                    JOIN course_requirement cr ON c.id = cr.course_id
                    JOIN university u ON cr.university_id = u.id
                    LEFT JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
                    WHERE (:state IS NULL OR u.state = :state)
                    AND (:program_type IS NULL OR u.program_type = :program_type)
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
            
            # Execute course query
            courses = db.session.execute(
                base_course_query,
                {
                    'state': state,
                    'program_type': program_type,
                    'query': query_text,
                    'like_query': f'%{query_text}%' if query_text else None,
                    'limit': per_page,
                    'offset': offset
                }
            ).mappings().all()
            
            # Get total course count
            total_courses = db.session.scalar(
                text("""
                    SELECT COUNT(*)
                    FROM course c
                    JOIN course_requirement cr ON c.id = cr.course_id
                    JOIN university u ON cr.university_id = u.id
                    WHERE (:state IS NULL OR u.state = :state)
                    AND (:program_type IS NULL OR u.program_type = :program_type)
                    AND (
                        :query IS NULL 
                        OR c.search_vector @@ plainto_tsquery('english', :query)
                        OR c.course_name ILIKE :like_query
                        OR c.code ILIKE :like_query
                    )
                """),
                {
                    'state': state,
                    'program_type': program_type,
                    'query': query_text,
                    'like_query': f'%{query_text}%' if query_text else None
                }
            )
            
            # Create paginated results
            results = {
                'universities': {
                    'items': universities,
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