# app/views/university.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from ..models.university import University, Course
from ..models.interaction import Bookmark
from ..extensions import db
from ..config import Config

bp = Blueprint("university", __name__)


@bp.route("/recommend", methods=["GET", "POST"])
def recommend():
    # Pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = 6

    # Get filter parameters
    location = request.args.get("location")
    programme_types = request.args.get("programme_type", "").split(",")
    preferred_university = request.args.get("university")
    preferred_course = request.args.get("course")

    try:
        # Start with base query
        base_query = db.session.query(University).distinct()

        # Add course join if course is specified
        if preferred_course:
            base_query = base_query.join(Course, University.courses)
            base_query = base_query.filter(Course.course_name == preferred_course)

        # Apply university filter if specified
        if preferred_university:
            base_query = base_query.filter(
                University.university_name == preferred_university
            )

        # Get all results before pagination to extract available filters
        all_results = base_query.all()

        # Extract available program types and states from current results
        available_program_types = sorted(
            list(set(uni.program_type for uni in all_results))
        )
        available_states = sorted(list(set(uni.state for uni in all_results)))

        # Now apply remaining filters to get final results
        query = base_query

        # Apply location filter
        if location:
            query = query.filter(University.state == location)

        # Handle programme types
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

        # Get total count and calculate pagination
        total_results = query.count()
        total_pages = (total_results + per_page - 1) // per_page

        # Apply pagination
        results = (
            query.order_by(University.university_name)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        current_app.logger.info(
            f"""
            Recommendation search:
            Location: {location}
            Programme Types: {programme_types}
            Course: {preferred_course}
            Page: {page}
            Found: {total_results} institutions
            Available Program Types: {available_program_types}
            Available States: {len(available_states)} states
        """
        )

        # Process results
        recommendations = []
        for uni in results:
            courses = []
            if preferred_course:
                courses = [
                    course
                    for course in uni.courses
                    if course.course_name == preferred_course
                ]
            else:
                courses = uni.courses

            if not preferred_course or courses:
                uni_data = {
                    "id": uni.id,
                    "university_name": uni.university_name,
                    "state": uni.state,
                    "program_type": uni.program_type,
                    "courses": [
                        {
                            "id": course.id,
                            "course_name": course.course_name,
                            "utme_requirements": course.utme_requirements,
                            "subjects": course.subjects,
                            "direct_entry_requirements": course.direct_entry_requirements,
                            "abbrv": course.abbrv,
                        }
                        for course in courses
                    ],
                    "selected_course": preferred_course,
                }
                recommendations.append(uni_data)

        # Get user bookmarks
        user_bookmarks = set()
        if current_user.is_authenticated:
            user_bookmarks = set(
                bookmark.university_id for bookmark in current_user.bookmarks
            )

        return render_template(
            "recommend.html",
            recommendations=recommendations,
            location=location,
            university=preferred_university,
            course=preferred_course,
            user_bookmarks=user_bookmarks,
            total_results=total_results,
            page=page,
            total_pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages,
            programme_types=programme_types if programme_types[0] else [],
            states=available_states,  # Use available states instead of all states
            available_program_types=available_program_types,  # Pass available program types
            available_states=available_states,  # Pass available states separately if needed
        )

    except Exception as e:
        current_app.logger.error(f"Error in recommendations: {str(e)}")
        return render_template(
            "recommend.html",
            recommendations=[],
            location=location,
            university=preferred_university,
            course=preferred_course,
            user_bookmarks=set(),
            total_results=0,
            page=1,
            total_pages=1,
            has_prev=False,
            has_next=False,
            programme_types=programme_types if programme_types[0] else [],
            states=[],
            available_program_types=[],
            available_states=[],
            error="An error occurred while getting recommendations. Please try again.",
        )


@bp.route("/course/<int:course_id>")
def get_course(course_id):
    course = Course.query.get_or_404(course_id)
    return jsonify(
        {
            "id": course.id,
            "course_name": course.course_name,
            "university_name": course.university_name,
            "utme_requirements": course.utme_requirements,
            "subjects": course.subjects,
            "direct_entry_requirements": course.direct_entry_requirements,
            "abbrv": course.abbrv,
        }
    )


@bp.route("/institution/<int:id>")
def institution_details(id):
    try:
        # Fetch the university by ID
        university = University.query.get_or_404(id)

        # Optionally, fetch related courses
        courses = Course.query.filter_by(
            university_name=university.university_name
        ).all()

        current_app.logger.info(f"Rendering details for University ID: {id}")

        return render_template(
            "institution_details.html", university=university, courses=courses
        )
    except Exception as e:
        current_app.logger.error(f"Error rendering institution details: {str(e)}")
        abort(500)
