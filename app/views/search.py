# app/views/search.py

from flask import Blueprint, jsonify, request, current_app
from ..utils.search import perform_search
from ..models.university import University
from ..extensions import db, cache

bp = Blueprint('search', __name__)

@bp.route('/api/search')
def api_search():
    """API search endpoint with proper error handling"""
    query_text = request.args.get('q', '').strip()
    state = request.args.get('state')
    program_type = request.args.get('program_type')
    page = request.args.get('page', 1, type=int)
    
    try:
        results = perform_search(
            query_text=query_text,
            state=state,
            program_type=program_type,
            page=page
        )
        
        return jsonify({
            'universities': [{
                'id': uni.id,
                'university_name': uni.university_name,
                'state': uni.state,
                'program_type': uni.program_type
            } for uni in results['universities'].items],
            'courses': [{
                'id': course.id,
                'course_name': course.course_name,
                'university_name': course.university_name,
                'abbrv': course.abbrv,
                'requirements': {
                    'direct_entry': course.direct_entry_requirements,
                    'utme': course.utme_requirements,
                    'subjects': course.subjects
                }
            } for course in results['courses'].items],
            'metadata': {
                'total_universities': results['total_universities'],
                'total_courses': results['total_courses'],
                'current_page': page,
                'has_next': results['universities'].has_next or results['courses'].has_next,
                'has_prev': results['universities'].has_prev or results['courses'].has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"API search error: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your search.'
        }), 500
