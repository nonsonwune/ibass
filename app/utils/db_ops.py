# app/utils/db_ops.py
from flask import current_app
from sqlalchemy import text
from ..extensions import db

def create_search_columns():
    """Create search vector columns if they don't exist"""
    try:
        current_app.logger.info("Checking and creating search vector columns...")
        
        # Create search_vector columns and indexes if they don't exist
        db.session.execute(text("""
            DO $$ 
            BEGIN
                -- Add search_vector column to university table if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'university' 
                    AND column_name = 'search_vector'
                ) THEN
                    ALTER TABLE university ADD COLUMN search_vector tsvector;
                    CREATE INDEX IF NOT EXISTS idx_university_search ON university USING gin(search_vector);
                END IF;

                -- Add search_vector column to course table if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'course' 
                    AND column_name = 'search_vector'
                ) THEN
                    ALTER TABLE course ADD COLUMN search_vector tsvector;
                    CREATE INDEX IF NOT EXISTS idx_course_search ON course USING gin(search_vector);
                END IF;
            END $$;
        """))
        
        db.session.commit()
        current_app.logger.info("Search vector columns created successfully")
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating search columns: {str(e)}")
        raise

def verify_search_columns():
    """Verify search vector columns exist"""
    try:
        # Check university table
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'university' 
            AND column_name = 'search_vector'
        """)).fetchone()
        
        if not result:
            current_app.logger.error("University search_vector column missing")
            return False
            
        # Check course table
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'course' 
            AND column_name = 'search_vector'
        """)).fetchone()
        
        if not result:
            current_app.logger.error("Course search_vector column missing")
            return False
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Database verification failed: {str(e)}")
        return False
    
def migrate_course_structure():
    """Migrate course data to new normalized structure"""
    try:
        current_app.logger.info("Starting course structure migration...")
        
        with db.session.begin_nested():
            # Step 1: Get existing course data
            old_courses = db.session.execute(text("""
                SELECT DISTINCT course_name, university_name, 
                       utme_requirements, direct_entry_requirements, 
                       subjects 
                FROM course
            """)).fetchall()
            
            # Step 2: Migrate unique courses
            current_app.logger.info("Migrating unique courses...")
            for course in old_courses:
                db.session.execute(text("""
                    INSERT INTO courses (name)
                    VALUES (:name)
                    ON CONFLICT (name) DO NOTHING
                """), {"name": course.course_name})
            
            # Step 3: Create course requirements
            current_app.logger.info("Creating course requirements...")
            for course in old_courses:
                course_id = db.session.execute(text("""
                    SELECT id FROM courses WHERE name = :name
                """), {"name": course.course_name}).scalar()
                
                university_id = db.session.execute(text("""
                    SELECT id FROM university 
                    WHERE university_name = :name
                """), {"name": course.university_name}).scalar()
                
                req_id = db.session.execute(text("""
                    INSERT INTO course_requirements 
                    (university_id, course_id, utme_requirements, direct_entry_requirements)
                    VALUES (:uni_id, :course_id, :utme, :de)
                    RETURNING id
                """), {
                    "uni_id": university_id,
                    "course_id": course_id,
                    "utme": course.utme_requirements,
                    "de": course.direct_entry_requirements
                }).scalar()
                
                # Step 4: Create subject requirements
                if course.subjects:
                    db.session.execute(text("""
                        INSERT INTO subject_requirements 
                        (course_requirement_id, subjects)
                        VALUES (:req_id, :subjects)
                    """), {
                        "req_id": req_id,
                        "subjects": course.subjects
                    })
        
        db.session.commit()
        current_app.logger.info("Course structure migration completed successfully")
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Course structure migration failed: {str(e)}")
        raise
    
def verify_course_migration():
    """Verify course migration was successful"""
    try:
        # Check course counts match
        old_count = db.session.execute(text("""
            SELECT COUNT(DISTINCT course_name) FROM course
        """)).scalar()
        
        new_count = db.session.execute(text("""
            SELECT COUNT(*) FROM courses
        """)).scalar()
        
        if old_count != new_count:
            current_app.logger.error(
                f"Course count mismatch: {old_count} vs {new_count}"
            )
            return False
            
        # Check requirements were created
        req_count = db.session.execute(text("""
            SELECT COUNT(*) FROM course_requirements
        """)).scalar()
        
        if req_count == 0:
            current_app.logger.error("No course requirements were created")
            return False
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Migration verification failed: {str(e)}")
        return False
    
def verify_migration_results():
    """Verify results of course structure migration"""
    try:
        results = {}
        
        # Get counts from all relevant tables
        counts = db.session.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM courses) as courses_count,
                (SELECT COUNT(*) FROM course_requirements) as requirements_count,
                (SELECT COUNT(*) FROM subject_requirements) as subjects_count,
                (SELECT COUNT(DISTINCT course_name) FROM course) as old_unique_courses,
                (SELECT COUNT(*) FROM course) as old_total_courses
        """)).fetchone()
        
        results = {
            'new_unique_courses': counts[0],
            'course_requirements': counts[1],
            'subject_requirements': counts[2],
            'old_unique_courses': counts[3],
            'old_total_courses': counts[4]
        }
        
        return results
        
    except Exception as e:
        current_app.logger.error(f"Verification query failed: {str(e)}")
        raise