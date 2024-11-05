# app/views/search.py

from flask import Blueprint, jsonify, request, current_app
from ..utils.search import perform_search
from ..models.university import University
from ..extensions import db, cache

bp = Blueprint('search', __name__)

@bp.route('/api/search')
def api_search():
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
                'id': uni['id'],
                'university_name': uni['university_name'],
                'state': uni['state'],
                'program_type': uni['program_type']
            } for uni in results['universities']['items']],
            'courses': [{
                'id': course['id'],
                'course_name': course['course_name'],
                'code': course.get('code'),
                'state': course.get('state'),
                'program_type': course.get('program_type'),
                'requirements': {
                    'direct_entry': course.get('direct_entry_requirements'),
                    'utme': course.get('utme_requirements'),
                    'subjects': course.get('subjects')
                }
            } for course in results['courses']['items']],
            'metadata': {
                'total_universities': results['universities']['total'],
                'total_courses': results['courses']['total'],
                'current_page': page,
                'has_next': results['universities']['has_next'] or results['courses']['has_next'],
                'has_prev': results['universities']['has_prev'] or results['courses']['has_prev']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"API search error: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your search.'
        }), 500