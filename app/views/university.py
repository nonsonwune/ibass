# app/views/university.py
from flask import Blueprint, render_template, request, jsonify, current_app, abort, flash, redirect, url_for
from flask_login import current_user
from sqlalchemy import func, distinct
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from ..models.university import University, Course, CourseRequirement, State, ProgrammeType
from ..models.interaction import Bookmark, Comment
from ..extensions import db
from ..config import Config
from ..forms.comment import CommentForm

bp = Blueprint("university", __name__)

@bp.route("/recommend")
def recommend():
    try:
        # Get filter parameters
        location = request.args.get('location', '')
        programme_types = request.args.get('programme_type', '').split(',')
        course = request.args.get('course', '')
        page = int(request.args.get('page', 1))
        per_page = 10

        # Build base query with eager loading
        query = University.query\
            .options(joinedload(University.state_info))\
            .options(joinedload(University.programme_type_info))\
            .options(joinedload(University.courses))\
            .join(State, University.state_id == State.id)\
            .join(ProgrammeType, University.programme_type_id == ProgrammeType.id)

        # If course is specified, join with course tables
        if course and course != 'ALL':
            query = query.join(CourseRequirement, University.id == CourseRequirement.university_id)\
                        .join(Course, Course.id == CourseRequirement.course_id)\
                        .filter(Course.course_name == course)

        # Apply filters
        if location:
            query = query.filter(State.name == location)
        
        if programme_types and programme_types[0]:
            query = query.filter(ProgrammeType.name.in_(programme_types))

        # Get total count before pagination
        total = query.count()
        
        # Add pagination
        paginated_unis = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format universities for display
        recommendations = []
        for uni in paginated_unis.items:
            uni_data = {
                'id': uni.id,
                'university_name': uni.university_name,
                'state': uni.state_info.name,  # Use state_info relationship
                'program_type': uni.programme_type_info.name,  # Use programme_type_info relationship
                'total_courses': len(uni.courses),
                'selected_course': course if course else None
            }
            recommendations.append(uni_data)

        # Get available filters based on current selection
        available_states = db.session.query(State.name)\
            .join(University)\
            .distinct()\
            .order_by(State.name)\
            .all()
        available_states = [state[0] for state in available_states]

        available_program_types = db.session.query(ProgrammeType.name)\
            .join(University)\
            .distinct()\
            .order_by(ProgrammeType.name)\
            .all()
        available_program_types = [pt[0] for pt in available_program_types]

        # Get active filters (those that would return results)
        active_query = University.query
        if course and course != 'ALL':
            active_query = active_query.join(CourseRequirement)\
                                     .join(Course)\
                                     .filter(Course.course_name == course)

        active_states = db.session.query(State.name)\
            .join(University, State.id == University.state_id)\
            .filter(University.id.in_(active_query.with_entities(University.id)))\
            .distinct()\
            .all()
        active_states = [state[0] for state in active_states]

        active_program_types = db.session.query(ProgrammeType.name)\
            .join(University, ProgrammeType.id == University.programme_type_id)\
            .filter(University.id.in_(active_query.with_entities(University.id)))\
            .distinct()\
            .all()
        active_program_types = [pt[0] for pt in active_program_types]

        # Get counts for filters
        state_counts = dict(
            db.session.query(State.name, func.count(University.id))
            .join(University, State.id == University.state_id)
            .group_by(State.name)
            .all()
        )

        program_type_counts = dict(
            db.session.query(ProgrammeType.name, func.count(University.id))
            .join(University, ProgrammeType.id == University.programme_type_id)
            .group_by(ProgrammeType.name)
            .all()
        )

        return render_template('recommend.html',
            recommendations=recommendations,
            total_results=total,
            page=page,
            per_page=per_page,
            total_pages=paginated_unis.pages,
            has_next=paginated_unis.has_next,
            has_prev=paginated_unis.has_prev,
            location=location,
            programme_types=programme_types,
            course=course,
            available_states=available_states,
            available_program_types=available_program_types,
            active_states=active_states,
            active_program_types=active_program_types,
            state_counts=state_counts,
            program_type_counts=program_type_counts,
            user_bookmarks=get_user_bookmarks() if current_user.is_authenticated else []
        )

    except Exception as e:
        current_app.logger.error(f"Error in recommendations: {str(e)}", exc_info=True)
        return render_template('recommend.html',
            recommendations=[],
            error="An error occurred while fetching recommendations."
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
        filtered_requirements = []
        if preferred_course:
            filtered_requirements = [
                req for req in uni.course_requirements
                if req.course.course_name == preferred_course
            ]
        else:
            filtered_requirements = uni.course_requirements
            
        if not preferred_course or filtered_requirements:
            requirement_data = []
            for req in filtered_requirements:
                requirement_data.append({
                    "id": req.course.id,
                    "course_name": req.course.course_name,
                    "utme_requirements": req.utme_requirements,
                    "subjects": req.subject_requirement.subjects if req.subject_requirement else None,
                    "direct_entry_requirements": req.direct_entry_requirements,
                })
            
            uni_data = {
                "id": uni.id,
                "university_name": uni.university_name,
                "state": uni.state,
                "program_type": uni.program_type,
                "website": uni.website,
                "established": uni.established,
                "abbrv": uni.abbrv,
                "total_courses": len(uni.course_requirements),
                "requirements": requirement_data,
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
        course = Course.query.join(
            CourseRequirement
        ).join(
            University
        ).filter(
            Course.id == course_id
        ).first_or_404()
        
        requirement = course.requirements[0] if course.requirements else None
        university = requirement.university if requirement else None
        
        return jsonify({
            "id": course.id,
            "course_name": course.course_name,
            "university_name": university.university_name if university else None,
            "utme_requirements": requirement.utme_requirements if requirement else None,
            "subjects": requirement.subject_requirement.subjects if requirement and requirement.subject_requirement else None,
            "direct_entry_requirements": requirement.direct_entry_requirements if requirement else None,
            "abbrv": university.abbrv if university else None,
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching course details: {str(e)}")
        abort(500)

@bp.route("/institution/<int:id>")
def institution_details(id):
    try:
        university = University.query.get_or_404(id)
        courses = university.courses
        
        # Use the unified Comment model
        comments = Comment.query.filter_by(
            university_id=id,  # Using university_id
            parent_id=None  # Get only top-level comments
        ).order_by(Comment.date_posted.desc()).all()
        
        return render_template('institution_details.html',
                             university=university,
                             courses=courses,
                             comments=comments)
    except Exception as e:
        current_app.logger.error(f"Error in institution_details: {str(e)}")
        flash('An error occurred while loading the institution details.', 'danger')
        return redirect(url_for('main.home'))

@bp.route("/institution/<int:id>/courses")
def get_institution_courses(id):
    try:
        # Get query parameters
        search_query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('COURSES_PER_PAGE', 10)

        # Build base query using relationships
        query = Course.query.join(
            CourseRequirement,
            CourseRequirement.course_id == Course.id
        ).filter(
            CourseRequirement.university_id == id
        )

        # Apply search filter if provided
        if search_query:
            search_terms = [term.strip() for term in search_query.split()]
            for term in search_terms:
                query = query.filter(Course.course_name.ilike(f'%{term}%'))

        # Get total count for pagination
        total_courses = query.count()
        total_pages = (total_courses + per_page - 1) // per_page

        # Apply pagination
        courses = (query
                  .order_by(Course.course_name)
                  .offset((page - 1) * per_page)
                  .limit(per_page)
                  .all())

        # Format response using relationships
        course_list = [{
            'id': course.id,
            'course_name': course.course_name,
            'requirements': [{
                'utme_requirements': req.utme_requirements,
                'direct_entry_requirements': req.direct_entry_requirements,
                'subjects': req.subject_requirement.subjects if req.subject_requirement else None
            } for req in course.requirements if req.university_id == id]
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
    try:
        query = request.args.get('q', '').strip()
        institution_id = request.args.get('institution_id')
        
        if not query or len(query) < 2:
            return jsonify([])

        # Start with base query
        course_query = Course.query.join(
            CourseRequirement
        ).join(
            University
        ).distinct(Course.course_name)

        # Add institution filter if provided
        if institution_id:
            course_query = course_query.filter(CourseRequirement.university_id == institution_id)

        # Get suggestions with count of institutions offering each course
        suggestions = (course_query
                     .filter(Course.course_name.ilike(f'%{query}%'))
                     .with_entities(
                         Course.course_name,
                         func.count(distinct(CourseRequirement.university_id)).label('institution_count')
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