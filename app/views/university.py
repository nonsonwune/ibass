from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from ..models.university import University, Course
from ..models.interaction import Bookmark
from ..extensions import db
from ..config import Config

bp = Blueprint('university', __name__)

@bp.route('/recommend', methods=['GET', 'POST'])
def recommend():
    location = request.args.get('location')
    programme_types = request.args.get('programme_type', '').split(',')
    preferred_university = request.args.get('university')
    preferred_course = request.args.get('course')

    try:
        # Start with base query
        query = db.session.query(University).distinct()

        # Add course join if course is specified
        if preferred_course:
            query = query.join(Course, University.courses)
            query = query.filter(Course.course_name == preferred_course)

        # Apply location filter
        if location:
            query = query.filter(University.state == location)

        # Handle multiple programme types
        if programme_types and programme_types[0]:  # Check if not empty string
            expanded_types = []
            for ptype in programme_types:
                ptype = ptype.strip()  # Remove any whitespace
                if ptype in Config.PROGRAMME_GROUPS:
                    expanded_types.extend(Config.PROGRAMME_GROUPS[ptype])
                else:
                    expanded_types.append(ptype)
            
            if expanded_types:
                query = query.filter(University.program_type.in_(expanded_types))

        # Apply university filter if specified
        if preferred_university:
            query = query.filter(University.university_name == preferred_university)

        # Execute query
        results = query.order_by(University.university_name).all()

        current_app.logger.info(f"""
            Recommendation search:
            Location: {location}
            Programme Types: {programme_types}
            Course: {preferred_course}
            Found: {len(results)} institutions
        """)

        # Process results
        recommendations = []
        for uni in results:
            # If course is specified, only include matching courses
            courses = []
            if preferred_course:
                courses = [course for course in uni.courses if course.course_name == preferred_course]
            else:
                courses = uni.courses

            if not preferred_course or courses:  # Only include if no course filter or has matching course
                uni_data = {
                    "id": uni.id,
                    "university_name": uni.university_name,
                    "state": uni.state,
                    "program_type": uni.program_type,
                    "courses": [{
                        "id": course.id,
                        "course_name": course.course_name,
                        "utme_requirements": course.utme_requirements,
                        "subjects": course.subjects,
                        "direct_entry_requirements": course.direct_entry_requirements,
                        "abbrv": course.abbrv,
                    } for course in courses],
                    "selected_course": preferred_course,
                }
                recommendations.append(uni_data)

        # Get user bookmarks
        user_bookmarks = set()
        if current_user.is_authenticated:
            user_bookmarks = set(bookmark.university_id for bookmark in current_user.bookmarks)

        return render_template('recommend.html',
            recommendations=recommendations,
            location=location,
            university=preferred_university,
            course=preferred_course,
            user_bookmarks=user_bookmarks,
        )

    except Exception as e:
        current_app.logger.error(f"Error in recommendations: {str(e)}")
        return render_template('recommend.html',
            recommendations=[],
            location=location,
            university=preferred_university,
            course=preferred_course,
            user_bookmarks=set(),
            error="An error occurred while getting recommendations. Please try again."
        )

@bp.route('/course/<int:course_id>')
def get_course(course_id):
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