# app/views/search.py

from flask import Blueprint, jsonify, request, current_app
from ..utils.search import perform_search
from ..extensions import db, cache
from ..models.university import University, Course, State, ProgrammeType
from ..models.requirement import CourseRequirement

bp = Blueprint("search", __name__)


def debug_search_params(query_text, state, program_type, page):
    """Log search parameters for debugging"""
    current_app.logger.debug(
        "Search Parameters:\n"
        f"Query: '{query_text}'\n"
        f"State: '{state}'\n"
        f"Program Type: '{program_type}'\n"
        f"Page: {page}"
    )


def debug_search_results(results):
    """Log search results for debugging"""
    current_app.logger.debug(
        "Search Results:\n"
        f"Universities found: {len(results['universities']['items'])}\n"
        f"Courses found: {len(results['courses']['items'])}\n"
        f"Total universities: {results['universities']['total']}\n"
        f"Total courses: {results['courses']['total']}"
    )


@bp.route("/api/search")
def api_search():
    """
    Unified search endpoint for universities and courses
    """
    try:
        query_text = request.args.get("q", "").strip()
        state = request.args.get("state")
        program_type = request.args.get("program_type")
        page = request.args.get("page", 1, type=int)

        current_app.logger.debug(
            f"Search request - query: {query_text}, state: {state}, "
            f"program_type: {program_type}, page: {page}"
        )

        # Build the base university query with proper joins
        universities_query = University.query.join(
            State, University.state_id == State.id
        ).join(ProgrammeType, University.programme_type_id == ProgrammeType.id)

        # Apply filters
        if query_text:
            universities_query = universities_query.filter(
                University.search_vector.match(query_text)
            )
        if state and state.lower() != "all":
            universities_query = universities_query.filter(State.name == state)
        if program_type:
            universities_query = universities_query.filter(
                ProgrammeType.name == program_type
            )

        # Execute paginated query
        universities = universities_query.paginate(
            page=page, per_page=10, error_out=False
        )

        # Build the base course query with proper joins
        courses_query = (
            Course.query.join(CourseRequirement)
            .join(University)
            .join(State)
            .join(ProgrammeType)
        )

        # Apply filters to courses
        if query_text:
            courses_query = courses_query.filter(Course.search_vector.match(query_text))
        if state and state.lower() != "all":
            courses_query = courses_query.filter(State.name == state)
        if program_type:
            courses_query = courses_query.filter(ProgrammeType.name == program_type)

        # Execute paginated query
        courses = courses_query.paginate(page=page, per_page=10, error_out=False)

        # Format response
        response = {
            "universities": {
                "items": [
                    {
                        "id": uni.id,
                        "university_name": uni.university_name,
                        "state": uni.state_info.name,  # Use the relationship
                        "program_type": uni.programme_type_info.name,  # Use the relationship
                    }
                    for uni in universities.items
                ],
                "total": universities.total,
                "has_next": universities.has_next,
                "has_prev": universities.has_prev,
                "page": page,
            },
            "courses": {
                "items": [
                    {
                        "id": course.id,
                        "course_name": course.course_name,
                        "code": course.code,
                        "state": (
                            course.universities[0].state_info.name
                            if course.universities
                            else None
                        ),
                        "program_type": (
                            course.universities[0].programme_type_info.name
                            if course.universities
                            else None
                        ),
                        "utme_requirements": (
                            course.requirements[0].utme_requirements
                            if course.requirements
                            else None
                        ),
                        "direct_entry_requirements": (
                            course.requirements[0].direct_entry_requirements
                            if course.requirements
                            else None
                        ),
                        "subjects": (
                            course.requirements[0].subject_requirement.subjects
                            if course.requirements
                            and course.requirements[0].subject_requirement
                            else None
                        ),
                    }
                    for course in courses.items
                ],
                "total": courses.total,
                "has_next": courses.has_next,
                "has_prev": courses.has_prev,
                "page": page,
            },
            "metadata": {
                "total_universities": universities.total,
                "total_courses": courses.total,
                "current_page": page,
                "has_next": universities.has_next or courses.has_next,
                "has_prev": universities.has_prev or courses.has_prev,
            },
        }

        current_app.logger.debug(f"Search response: {response}")
        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"API search error: {str(e)}", exc_info=True)
        return (
            jsonify(
                {
                    "error": "An error occurred while processing your search.",
                    "details": str(e) if current_app.debug else None,
                }
            ),
            500,
        )
