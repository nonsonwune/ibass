# app/utils/startup.py

from flask import current_app
from sqlalchemy import inspect
from ..extensions import db  # Add this import
from .db_ops import verify_search_columns, create_search_columns
from .search import init_search_vectors
import time

def verify_database_setup():
    """Verify database setup on application startup with progress monitoring"""
    start_time = time.time()
    try:
        current_app.logger.info("Starting database verification and setup...")
        
        # Add table verification with more detailed logging
        required_tables = [
            'subjects', 
            'subject_categories', 
            'course_requirement_template'
        ]
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        current_app.logger.info("Checking required tables...")
        for table in required_tables:
            if table in existing_tables:
                current_app.logger.info(f"  ✓ {table} exists")
            else:
                current_app.logger.error(f"  ✗ {table} missing")
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            current_app.logger.error(f"Missing required tables: {missing_tables}")
            return False
            
        # Continue with existing verification steps
        current_app.logger.info("Step 1/3: Verifying search columns...")
        if not verify_search_columns():
            current_app.logger.info("Step 2/3: Creating missing columns...")
            create_search_columns()
        else:
            current_app.logger.info("Step 2/3: Columns already exist, skipping creation")
        
        # Initialize vectors
        current_app.logger.info("Step 3/3: Initializing search vectors...")
        init_search_vectors()
        
        elapsed_time = time.time() - start_time
        current_app.logger.info(
            f"Database verification and setup completed successfully in {elapsed_time:.1f} seconds"
        )
        return True
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        current_app.logger.error(
            f"Database setup failed after {elapsed_time:.1f} seconds: {str(e)}"
        )
        # Don't raise the exception - allow the app to start with degraded functionality
        return False

def verify_tables_exist():
    """Separate function to verify specific tables exist"""
    try:
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = ['subjects', 'subject_categories', 'course_requirement_template']
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            current_app.logger.error(f"Missing required tables: {missing_tables}")
            return False
        return True
    except Exception as e:
        current_app.logger.error(f"Error verifying tables: {str(e)}")
        return False