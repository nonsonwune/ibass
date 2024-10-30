# app/views/university.py
from flask import Blueprint, render_template, request, jsonify, current_app, abort
from flask_login import current_user
from sqlalchemy import func, distinct
from sqlalchemy.exc import SQLAlchemyError
from ..models.university import University, Course
from ..models.interaction import Bookmark
from ..extensions import db
from ..config import Config

bp = Blueprint("university", __name__)

@bp.route("/recommend", methods=["GET"])
def recommend():
    try:
        # Get pagination and filter parameters
        page = request.args.get("page", 1, type=int)
        location = request.args.get("location")
        programme_types = request.args.get("programme_type", "").split(",")
        preferred_course = request.args.get("course")
        
        per_page = current_app.config.get('RESULTS_PER_PAGE', 6)

        # Start with base query including course join if needed
        base_query = db.session.query(University).distinct()
        
        if preferred_course:
            base_query = base_query.join(Course, University.courses)
            base_query = base_query.filter(Course.course_name == preferred_course)

        # Get filter counts and available options before applying remaining filters
        filter_results = get_filter_counts_and_options(base_query, location)

        # Apply remaining filters
        query = apply_filters(base_query, location, programme_types)
        
        # Get active filters for current result set
        active_filters = get_active_filters(query)
        
        # Get paginated results
        pagination_data = get_paginated_results(query, page, per_page)
        
        # Process and format university results
        formatted_results = format_university_results(
            pagination_data['results'], 
            preferred_course
        )

        # Get user bookmarks if authenticated
        user_bookmarks = get_user_bookmarks()

        # Prepare template data
        template_data = {
            'recommendations': formatted_results,
            'location': location,
            'course': preferred_course,
            'user_bookmarks': user_bookmarks,
            'total_results': pagination_data['total_results'],
            'page': page,
            'total_pages': pagination_data['total_pages'],
            'has_prev': pagination_data['has_prev'],
            'has_next': pagination_data['has_next'],
            'programme_types': programme_types if programme_types[0] else [],
            **filter_results,
            **active_filters
        }

        return render_template("recommend.html", **template_data)

    except Exception as e:
        current_app.logger.error(f"Error in recommendations: {str(e)}")
        return render_template("recommend.html", 
            recommendations=[],
            error="An error occurred while getting recommendations. Please try again.",
            **get_empty_template_data(location, programme_types, preferred_course)
        )

def get_filter_counts_and_options(query, location=None):
    """Get counts and available options for filters with state context"""
    # Start with base query that will be used for all counts
    base_count_query = query
    
    # If location is selected, use it for getting program type counts
    if location:
        program_type_counts = dict(
            base_count_query.filter(University.state == location)
            .with_entities(
                University.program_type,
                func.count(distinct(University.id)).label('count')
            )
            .group_by(University.program_type)
            .all()
        )
    else:
        # If no location selected, get total counts for each program type
        program_type_counts = dict(
            base_count_query
            .with_entities(
                University.program_type,
                func.count(distinct(University.id)).label('count')
            )
            .group_by(University.program_type)
            .all()
        )

    # Get state counts (these remain global to show available options)
    state_counts = dict(
        base_count_query
        .with_entities(
            University.state,
            func.count(distinct(University.id)).label('count')
        )
        .group_by(University.state)
        .all()
    )
    
    return {
        'state_counts': state_counts,
        'program_type_counts': program_type_counts,
        'available_states': sorted(state_counts.keys()),
        'available_program_types': sorted(program_type_counts.keys())
    }

def apply_filters(query, location, programme_types):
    """Apply location and program type filters to query"""
    if location:
        query = query.filter(University.state == location)

    if programme_types and programme_types[0]:
        expanded_types = []
        for ptype in programme_types:
            ptype = ptype.strip()
            if ptype in Config.PROGRAMME_GROUPS:
                expanded_types.extend(Config.PROGRAMME_GROUPS[ptype])
            else:
                expanded_types.append(ptype)

        if expanded_types:
            query = query.filter(University.program_type.in_(expanded_types))
    
    return query

def get_active_filters(query):
    """Get currently active filter options"""
    return {
        'active_states': [
            r[0] for r in query.with_entities(University.state)
            .distinct()
            .order_by(University.state)
            .all()
        ],
        'active_program_types': [
            r[0] for r in query.with_entities(University.program_type)
            .distinct()
            .order_by(University.program_type)
            .all()
        ]
    }

def get_paginated_results(query, page, per_page):
    """Get paginated results and pagination data"""
    total_results = query.count()
    total_pages = (total_results + per_page - 1) // per_page
    
    results = (
        query.order_by(University.university_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    
    return {
        'results': results,
        'total_results': total_results,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }

def format_university_results(universities, preferred_course=None):
    formatted_results = []
    
    for uni in universities:
        courses = uni.courses
        filtered_courses = [
            course for course in courses
            if not preferred_course or course.course_name == preferred_course
        ]
        
        if not preferred_course or filtered_courses:
            uni_data = {
                "id": uni.id,
                "university_name": uni.university_name,
                "state": uni.state,
                "program_type": uni.program_type,
                "website": uni.website,
                "established": uni.established,
                "abbrv": uni.abbrv,  # Added this line
                "total_courses": len(courses),
                "courses": [{
                    "id": course.id,
                    "course_name": course.course_name,
                    "utme_requirements": course.utme_requirements,
                    "subjects": course.subjects,
                    "direct_entry_requirements": course.direct_entry_requirements,
                } for course in filtered_courses],
                "selected_course": preferred_course
            }
            formatted_results.append(uni_data)
    
    return formatted_results

def get_user_bookmarks():
    """Get user bookmarks if authenticated"""
    if current_user.is_authenticated:
        return set(bookmark.university_id for bookmark in current_user.bookmarks)
    return set()

def get_empty_template_data(location, programme_types, course):
    """Get empty template data for error state"""
    return {
        'location': location,
        'course': course,
        'user_bookmarks': set(),
        'total_results': 0,
        'page': 1,
        'total_pages': 1,
        'has_prev': False,
        'has_next': False,
        'programme_types': programme_types if programme_types[0] else [],
        'available_program_types': [],
        'available_states': [],
        'state_counts': {},
        'program_type_counts': {},
        'active_states': [],
        'active_program_types': []
    }

@bp.route("/course/<int:course_id>")
def get_course(course_id):
    try:
        course = Course.query.get_or_404(course_id)
        return jsonify({
            "id": course.id,
            "course_name": course.course_name,
            "university_name": course.university_name,
            "utme_requirements": course.utme_requirements,
            "subjects": course.subjects,
            "direct_entry_requirements": course.direct_entry_requirements,
            "abbrv": course.abbrv,
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching course details: {str(e)}")
        abort(500)

@bp.route("/institution/<int:id>")
def institution_details(id):
    try:
        university = University.query.get_or_404(id)
        
        # Optimize course query with a single database hit
        courses = (Course.query
                  .filter_by(university_name=university.university_name)
                  .order_by(Course.course_name)
                  .all())

        current_app.logger.info(f"Rendering details for University ID: {id}")

        return render_template(
            "institution_details.html",
            university=university,
            courses=courses
        )
    except Exception as e:
        current_app.logger.error(f"Error rendering institution details: {str(e)}")
        abort(500)

@bp.route("/institution/<int:id>/courses")
def get_institution_courses(id):
    """Get courses for an institution with optional filtering"""
    try:
        # Get query parameters
        search_query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('COURSES_PER_PAGE', 10)

        # Get base query
        university = University.query.get_or_404(id)
        query = Course.query.filter_by(university_name=university.university_name)

        # Apply search filter if provided
        if search_query:
            search_terms = [term.strip() for term in search_query.split()]
            for term in search_terms:
                query = query.join(University).filter(
                    Course.course_name.ilike(f'%{term}%') |
                    University.abbrv.ilike(f'%{term}%')
                )

        # Get total count for pagination
        total_courses = query.count()
        total_pages = (total_courses + per_page - 1) // per_page

        # Apply pagination
        courses = (query
                  .order_by(Course.course_name)
                  .offset((page - 1) * per_page)
                  .limit(per_page)
                  .all())

        # Format response
        course_list = [{
            'id': course.id,
            'course_name': course.course_name,
            'abbrv': course.abbrv,
            'utme_requirements': course.utme_requirements,
            'subjects': course.subjects,
            'direct_entry_requirements': course.direct_entry_requirements
        } for course in courses]

        return jsonify({
            'courses': course_list,
            'total': total_courses,
            'page': page,
            'pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching institution courses: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch courses',
            'message': str(e)
        }), 500

@bp.route("/institutions/suggest")
def suggest_institutions():
    """Endpoint for institution name autocomplete suggestions"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify([])

        # Get suggestions limited to 10 results
        suggestions = (University.query
                     .filter(University.university_name.ilike(f'%{query}%'))
                     .with_entities(
                         University.id,
                         University.university_name,
                         University.state,
                         University.program_type
                     )
                     .order_by(University.university_name)
                     .limit(10)
                     .all())

        return jsonify([{
            'id': s.id,
            'name': s.university_name,
            'state': s.state,
            'type': s.program_type
        } for s in suggestions])

    except Exception as e:
        current_app.logger.error(f"Error in institution suggestions: {str(e)}")
        return jsonify([])

@bp.route("/courses/suggest")
def suggest_courses():
    """Endpoint for course name autocomplete suggestions"""
    try:
        query = request.args.get('q', '').strip()
        institution_id = request.args.get('institution_id')
        
        if not query or len(query) < 2:
            return jsonify([])

        # Start with base query
        course_query = Course.query.distinct(Course.course_name)

        # Add institution filter if provided
        if institution_id:
            university = University.query.get_or_404(institution_id)
            course_query = course_query.filter_by(university_name=university.university_name)

        # Get suggestions with count of institutions offering each course
        suggestions = (course_query
                     .filter(Course.course_name.ilike(f'%{query}%'))
                     .with_entities(
                         Course.course_name,
                         func.count(distinct(Course.university_name)).label('institution_count')
                     )
                     .group_by(Course.course_name)
                     .order_by(Course.course_name)
                     .limit(10)
                     .all())

        return jsonify([{
            'name': s.course_name,
            'institutions': s.institution_count
        } for s in suggestions])

    except Exception as e:
        current_app.logger.error(f"Error in course suggestions: {str(e)}")
        return jsonify([])

def init_app(app):
    """Initialize blueprint with app context"""
    app.register_blueprint(bp, url_prefix='/university')