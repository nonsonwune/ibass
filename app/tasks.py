from flask import current_app
from .extensions import db

def refresh_course_view():
    """Refresh the course materialized view"""
    try:
        db.session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY course_university_view")
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error refreshing course view: {str(e)}")
        db.session.rollback() 