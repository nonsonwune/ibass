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

        # Use the search utility function
        results = perform_search(query_text, state, program_type, page)
        
        # Format response using the correct attribute names
        response = {
            "universities": {
                "items": [
                    {
                        "id": uni['id'],
                        "university_name": uni['university_name'],
                        "state": uni['state_name'],  # Match the column alias from search query
                        "program_type": uni['program_type_name'],  # Match the column alias from search query
                    }
                    for uni in results['universities']['items']
                ],
                "total": results['universities']['total'],
                "has_next": results['universities']['has_next'],
                "has_prev": results['universities']['has_prev'],
                "page": page,
            },
            "courses": results['courses'],  # Keep courses as is
            "metadata": {
                "total_universities": results['universities']['total'],
                "total_courses": results['courses']['total'],
                "current_page": page,
                "has_next": results['universities']['has_next'] or results['courses']['has_next'],
                "has_prev": results['universities']['has_prev'] or results['courses']['has_prev'],
            },
        }

        current_app.logger.debug(f"Search response: {response}")
        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"API search error: {str(e)}", exc_info=True)
        return jsonify({
            "error": "An error occurred while processing your search.",
            "details": str(e) if current_app.debug else None,
        }), 500
