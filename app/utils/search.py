# app/utils/search.py
from ..extensions import db, cache
from ..models.university import University, Course
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

def init_search_vectors():
    """Initialize search vectors for existing records with better error handling"""
    try:
        # Disable autoflush to prevent premature updates
        with db.session.no_autoflush:
            # Update universities
            universities = University.query.all()
            current_app.logger.info(f"Updating search vectors for {len(universities)} universities")
            
            # Batch update universities
            for idx, university in enumerate(universities, 1):
                search_text = ' '.join(filter(None, [
                    university.university_name,
                    university.state,
                    university.program_type
                ]))
                
                db.session.execute(
                    text("""
                        UPDATE university 
                        SET search_vector = to_tsvector('english', :search_text)
                        WHERE id = :id
                    """),
                    {
                        'search_text': search_text,
                        'id': university.id
                    }
                )
                
                if idx % 100 == 0:  # Commit every 100 records
                    db.session.commit()
                    current_app.logger.info(f"Processed {idx} universities")
            
            db.session.commit()
            current_app.logger.info("University search vectors updated successfully")
            
            # Update courses
            courses = Course.query.all()
            current_app.logger.info(f"Updating search vectors for {len(courses)} courses")
            
            # Batch update courses
            for idx, course in enumerate(courses, 1):
                search_text = ' '.join(filter(None, [
                    course.course_name,
                    course.abbrv or '',
                    course.subjects or ''
                ]))
                
                db.session.execute(
                    text("""
                        UPDATE course 
                        SET search_vector = to_tsvector('english', :search_text)
                        WHERE id = :id
                    """),
                    {
                        'search_text': search_text,
                        'id': course.id
                    }
                )
                
                if idx % 100 == 0:  # Commit every 100 records
                    db.session.commit()
                    current_app.logger.info(f"Processed {idx} courses")
            
            db.session.commit()
            current_app.logger.info("Course search vectors updated successfully")
            
    except Exception as e:
        current_app.logger.error(f"Error updating search vectors: {str(e)}")
        db.session.rollback()
        raise
    
def perform_search(query_text, state=None, program_type=None, page=1, per_page=10):
    """Unified search function with caching"""
    cache_key = f'search:{query_text}:{state}:{program_type}:{page}'
    results = cache.get(cache_key)
    
    if results is None:
        try:
            # Perform university search
            universities = University.search(query_text, state, program_type)\
                .paginate(page=page, per_page=per_page, error_out=False)
            
            # Perform course search
            courses = Course.search(query_text, program_type=program_type)\
                .paginate(page=page, per_page=per_page, error_out=False)
            
            results = {
                'universities': universities,
                'courses': courses,
                'total_universities': universities.total,
                'total_courses': courses.total
            }
            
            cache.set(cache_key, results, timeout=300)  # Cache for 5 minutes
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Search error: {str(e)}")
            raise
            
    return results