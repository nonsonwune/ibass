from flask import current_app
from .db_ops import verify_search_columns, create_search_columns
from .search import init_search_vectors
import time

def verify_database_setup():
    """Verify database setup on application startup with progress monitoring"""
    start_time = time.time()
    try:
        current_app.logger.info("Starting database verification and setup...")
        
        # Check if columns exist
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
        # Allow application to continue with degraded search functionality
        current_app.logger.warning(
            "Application will start with degraded search functionality"
        )
        return False