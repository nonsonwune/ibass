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