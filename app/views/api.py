# app/views/api.py

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from ..models.university import University, Course, CourseRequirement
from ..models.interaction import Bookmark, Comment, Vote
from ..models.user import User
from ..extensions import db
from ..config import Config
from ..utils.decorators import admin_required
import bleach
from sqlalchemy import text

bp = Blueprint('api', __name__)

# Define allowed tags and attributes for sanitization
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title']
}

@bp.route('/locations')
def get_locations():
    try:
        locations = University.get_all_states()
        # Add "All States" as the first option
        locations.insert(0, "ALL")
        current_app.logger.info(f"Retrieved {len(locations)} locations including ALL option")
        return jsonify(locations)
    except Exception as e:
        current_app.logger.error(f"Error retrieving locations: {str(e)}")
        return jsonify({"error": "Failed to retrieve locations"}), 500

@bp.route('/programme_types', methods=['GET'])
def get_programme_types():
    state = request.args.get('state')
    try:
        if state:
            programme_types = (
                db.session.query(University.program_type)
                .filter(University.state == state)
                .distinct()
                .order_by(University.program_type)
                .all()
            )
        else:
            programme_types = (
                db.session.query(University.program_type)
                .distinct()
                .order_by(University.program_type)
                .all()
            )

        # Convert list of tuples to list of strings
        programme_types_list = [ptype[0] for ptype in programme_types]

        # Add "ALL_INSTITUTION_TYPES" as the first option if not already present
        if programme_types_list and "ALL_INSTITUTION_TYPES" not in programme_types_list:
            programme_types_list.insert(0, "ALL_INSTITUTION_TYPES")

        # Sort programme types alphabetically, keeping "ALL_INSTITUTION_TYPES" at the top
        if "ALL_INSTITUTION_TYPES" in programme_types_list:
            all_institution = programme_types_list.pop(
                programme_types_list.index("ALL_INSTITUTION_TYPES")
            )
            programme_types_list.sort()
            programme_types_list.insert(0, all_institution)
        else:
            programme_types_list.sort()

        current_app.logger.info(f"Retrieved {len(programme_types_list)} programme types for state: {state}")
        return jsonify(programme_types_list)
    except Exception as e:
        current_app.logger.error(f"Error in get_programme_types: {str(e)}")
        return jsonify({"error": "An error occurred while fetching programme types."}), 500

@bp.route('/universities', methods=['GET'])
def get_universities():
    state = request.args.get('state')
    try:
        if state:
            universities = University.query.filter_by(state=state).all()
        else:
            universities = University.query.all()
        return jsonify([{
            "university_name": uni.university_name,
            "state": uni.state,
            "program_type": uni.program_type,
        } for uni in universities])
    except Exception as e:
        current_app.logger.error(f"Error retrieving universities: {str(e)}")
        return jsonify({"error": "Failed to retrieve universities."}), 500

@bp.route('/courses')
def get_courses():
    try:
        state = request.args.get('state')
        program_types = request.args.get('programme_type', '').split(',')
        load_all = request.args.get('load_all', 'false').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = 1000 if load_all else 50
        
        base_query = """
            WITH grouped_courses AS (
                SELECT 
                    c.id,
                    c.course_name,
                    c.code,
                    COUNT(DISTINCT u.id) as institution_count,
                    array_agg(
                        DISTINCT jsonb_build_object(
                            'university_name', u.university_name,
                            'state', u.state,
                            'program_type', u.program_type
                        )
                    ) as institutions
                FROM course c
                JOIN course_requirement cr ON c.id = cr.course_id
                JOIN university u ON u.id = cr.university_id
                WHERE 1=1
        """
        params = {}
        
        if program_types and program_types[0]:
            base_query += " AND u.program_type = ANY(:program_types)"
            params['program_types'] = program_types
            
        if state and state != 'ALL':
            base_query += " AND u.state = :state"
            params['state'] = state
            
        base_query += """
                GROUP BY c.id, c.course_name, c.code
            ),
            distinct_courses AS (
                SELECT DISTINCT ON (LOWER(course_name))
                    id,
                    course_name,
                    code,
                    institution_count,
                    institutions
                FROM grouped_courses
                ORDER BY LOWER(course_name), institution_count DESC
            )
            SELECT 
                id,
                course_name,
                code,
                institution_count,
                institutions
            FROM distinct_courses
            ORDER BY course_name
        """
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM (" + base_query + ") AS count_query"
        total = db.session.execute(text(count_query), params).scalar()
        
        if not load_all:
            base_query += " LIMIT :limit OFFSET :offset"
            params['limit'] = per_page
            params['offset'] = (page - 1) * per_page
        
        results = db.session.execute(text(base_query), params).fetchall()
        
        courses = [{
            'id': row.id,
            'course_name': row.course_name,
            'code': row.code or '',
            'institution_count': row.institution_count,
            'institutions': row.institutions
        } for row in results]
        
        current_app.logger.info(f"Found {len(courses)} unique courses out of {total} total matches")
        
        return jsonify({
            'courses': courses,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving courses: {str(e)}")
        return jsonify({'error': 'Failed to retrieve courses'}), 500

def validate_course_data(course, requirements):
    """Validate course data before sending"""
    try:
        return {
            "id": course.id,
            "course_name": course.course_name,
            "utme_requirements": requirements.get('utme'),
            "direct_entry_requirements": requirements.get('de'),
            "subjects": requirements.get('subjects')
        }
    except Exception as e:
        current_app.logger.error(f"Error validating course data: {str(e)}")
        return None

@bp.route('/institution/<int:uni_id>')
def get_institution_details(uni_id):
    try:
        selected_course = request.args.get('selected_course')
        university = University.query.get_or_404(uni_id)
        
        current_app.logger.debug(f"Fetching courses for university {uni_id}")
        
        # Get all requirements first
        requirements = CourseRequirement.get_course_requirements(uni_id)
        
        # Log requirement details
        current_app.logger.info(f"Found {len(requirements)} requirements for university {uni_id}")
        
        # Create requirements lookup dict with logging
        req_lookup = {req.course_id: req for req in requirements} if requirements else {}
        current_app.logger.debug(f"Created lookup for {len(req_lookup)} requirements")
        
        courses = (Course.query
                  .join(CourseRequirement, Course.id == CourseRequirement.course_id)
                  .filter(CourseRequirement.university_id == uni_id)
                  .order_by(Course.course_name)
                  .all())

        # Log course details
        current_app.logger.info(f"Found {len(courses)} courses for university {uni_id}")
        course_data = []
        
        for course in courses:
            req = req_lookup.get(course.id)
            current_app.logger.debug(
                f"Processing course {course.id} ({course.course_name}): "
                f"Has requirement: {bool(req)}"
            )
            
            if req:
                current_app.logger.debug(
                    f"Requirements for course {course.id}: "
                    f"UTME: {bool(req.utme_requirements)}, "
                    f"DE: {bool(req.direct_entry_requirements)}, "
                    f"Subjects: {bool(req.get_subjects())}"
                )
            
            course_data.append({
                "id": course.id,
                "course_name": course.course_name,
                "utme_requirements": (
                    req.utme_requirements 
                    if req and req.utme_template 
                    else "[Not Available]"  # Changed to explicit message
                ),
                "direct_entry_requirements": (
                    req.direct_entry_requirements 
                    if req and req.de_template 
                    else "[Not Available]"  # Changed to explicit message
                ),
                "subjects": (
                    req.get_subjects() 
                    if req and req.subject_requirement 
                    else "[Not Available]"  # Changed to explicit message
                )
            })

        response_data = {
            "id": university.id,
            "university_name": university.university_name,
            "state": university.state,
            "program_type": university.program_type,
            "website": university.website,
            "established": university.established,
            "abbrv": university.abbrv,
            "selected_course": selected_course,
            "courses": course_data
        }

        if not requirements:
            current_app.logger.warning(
                f"No requirements found for university {uni_id}. "
                f"Found {len(courses)} courses without requirements."
            )

        return jsonify(response_data), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_institution_details: {str(e)}", exc_info=True)
        return jsonify({
            "error": "An error occurred while fetching institution details.",
            "details": str(e) if current_app.debug else None
        }), 500

@bp.route('/bookmark', methods=['POST'])
@login_required
def add_bookmark():
    data = request.get_json()
    university_id = data.get('university_id')

    if not university_id:
        return jsonify({"success": False, "message": "Invalid university."}), 400

    try:
        existing_bookmark = Bookmark.query.filter_by(
            user_id=current_user.id,
            university_id=university_id
        ).first()
        
        if existing_bookmark:
            return jsonify({"success": True, "message": "Already bookmarked"}), 200

        bookmark = Bookmark(user_id=current_user.id, university_id=university_id)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Institution bookmarked successfully."
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding bookmark: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An error occurred while bookmarking. Please try again."
        }), 500

@bp.route('/user_bookmarks', methods=['GET'])
@login_required
def get_user_bookmarks():
    try:
        bookmarks = [bookmark.university_id for bookmark in current_user.bookmarks]
        return jsonify(bookmarks)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching user bookmarks: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error retrieving bookmark data'
        }), 500

@bp.route('/remove_bookmark/<int:university_id>', methods=['POST'])
@login_required
def remove_bookmark(university_id):
    current_app.logger.info(f"Attempting to remove bookmark for university {university_id}, user {current_user.id}")
    try:
        bookmark = Bookmark.query.filter_by(
            user_id=current_user.id,
            university_id=university_id
        ).first()
        
        if bookmark:
            current_app.logger.info(f"Found bookmark to remove: {bookmark.id}")
            db.session.delete(bookmark)
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "Bookmark removed successfully."
            }), 200
        else:
            current_app.logger.warning(f"No bookmark found for university {university_id} and user {current_user.id}")
            return jsonify({
                "success": False,
                "message": "Bookmark not found."
            }), 404
            
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing bookmark: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An error occurred while removing the bookmark."
        }), 500

@contextmanager
def atomic_transaction():
    """Ensure atomic transaction with proper error handling."""
    try:
        yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Transaction failed: {str(e)}")
        raise
    finally:
        db.session.close()

@bp.route('/vote/<int:comment_id>/<vote_type>', methods=['POST'])
@login_required
def vote(comment_id, vote_type):
    if vote_type not in ['like', 'dislike']:
        return jsonify({'success': False, 'message': 'Invalid vote type'}), 400

    try:
        with db.session.begin_nested():
            comment = Comment.query.get_or_404(comment_id)
            comment_author = User.query.get_or_404(comment.user_id)
            existing_vote = Vote.query.filter_by(
                user_id=current_user.id,
                comment_id=comment_id
            ).first()

            if existing_vote:
                if existing_vote.vote_type == vote_type:
                    # Remove vote if clicking same button
                    if vote_type == 'like':
                        comment.likes -= 1
                        comment_author.score -= 1
                    else:
                        comment.dislikes -= 1
                        comment_author.score += 1  # Removing a dislike increases score
                    db.session.delete(existing_vote)
                    current_vote = None
                else:
                    # Change vote type
                    if vote_type == 'like':
                        comment.likes += 1
                        comment.dislikes -= 1
                        comment_author.score += 2  # +2 for changing dislike to like
                    else:
                        comment.likes -= 1
                        comment.dislikes += 1
                        comment_author.score -= 2  # -2 for changing like to dislike
                    existing_vote.vote_type = vote_type
                    current_vote = vote_type
            else:
                # New vote
                new_vote = Vote(
                    user_id=current_user.id,
                    comment_id=comment_id,
                    vote_type=vote_type
                )
                if vote_type == 'like':
                    comment.likes += 1
                    comment_author.score += 1
                else:
                    comment.dislikes += 1
                    comment_author.score -= 1
                db.session.add(new_vote)
                current_vote = vote_type

            db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Vote recorded successfully',
            'likes': comment.likes,
            'dislikes': comment.dislikes,
            'user_vote': current_vote,
            'user_id': comment.user_id,
            'user_score': comment_author.score
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing vote: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing vote: {str(e)}'
        }), 500

@bp.route('/user_votes', methods=['GET'])
@login_required
def get_user_votes():
    try:
        votes = {}
        user_votes = Vote.query.filter_by(user_id=current_user.id).all()
        for vote in user_votes:
            votes[vote.comment_id] = vote.vote_type
        return jsonify(votes)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching user votes: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error retrieving vote data'
        }), 500

@bp.route('/search', methods=['GET'])
def search():
    query_text = request.args.get("q", "").lower()
    state = request.args.get("state")
    program_type = request.args.get("program_type")

    try:
        universities_query = University.query.filter(
            University.university_name.ilike(f"%{query_text}%")
        )
        if state:
            universities_query = universities_query.filter(
                University.state.ilike(f"%{state}%")
            )
        if program_type:
            universities_query = universities_query.filter(
                University.program_type.ilike(f"%{program_type}%")
            )
        universities = universities_query.all()

        courses_query = Course.query.join(
            CourseRequirement,
            CourseRequirement.course_id == Course.id
        ).join(
            University,
            University.id == CourseRequirement.university_id
        ).filter(
            (Course.course_name.ilike(f"%{query_text}%")) |
            (University.abbrv.ilike(f"%{query_text}%"))
        )
        courses = courses_query.all()

        return jsonify({
            "universities": [
                {
                    "university_name": uni.university_name,
                    "state": uni.state,
                    "program_type": uni.program_type,
                }
                for uni in universities
            ],
            "courses": [
                {
                    "id": course.id,
                    "course_name": course.course_name,
                    "requirements": [{
                        "university_name": req.university.university_name,
                        "abbrv": req.university.abbrv,
                        "direct_entry_requirements": req.direct_entry_requirements,
                        "utme_requirements": req.utme_requirements,
                        "subjects": req.subject_requirement.subjects if req.subject_requirement else None
                    } for req in course.requirements]
                }
                for course in courses
            ],
        })
    except Exception as e:
        current_app.logger.error(f"Error in search: {str(e)}")
        return jsonify({
            "error": "An error occurred while processing your search."
        }), 500

@bp.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        # Check if user has permission to delete
        if not (current_user.id == comment.user_id or current_user.is_admin):
            return jsonify({
                'success': False,
                'message': 'You do not have permission to delete this comment.'
            }), 403
            
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while deleting the comment'
        }), 400

@bp.route('/admin/search_courses', methods=['GET'])
@login_required
@admin_required
def search_courses():
    query = request.args.get('query', '').strip()
    try:
        if query:
            # Using ilike for case-insensitive search
            courses = Course.query.filter(
                db.or_(
                    Course.course_name.ilike(f'%{query}%'),
                    Course.abbrv.ilike(f'%{query}%')
                )
            ).order_by(Course.course_name).all()
        else:
            return jsonify({'courses': []})

        courses_data = [{
            'id': course.id,
            'course_name': course.course_name,
            'university_name': course.university_name,
            'abbrv': course.abbrv or ''  # Ensure abbrv is never null
        } for course in courses]

        return jsonify({'courses': courses_data})
    except Exception as e:
        current_app.logger.error(f"Error in course search: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@bp.route('/course/<int:course_id>', methods=['GET'])
def get_course_details(course_id):
    try:
        course = (Course.query
                 .join(CourseRequirement)
                 .join(University,  # Add this join
                      University.id == CourseRequirement.university_id)
                 .filter(Course.id == course_id)
                 .options(joinedload(Course.requirements)
                         .joinedload(CourseRequirement.university))  # Add eager loading
                 .first_or_404())
                 
        requirement = course.requirements[0] if course.requirements else None
        university = requirement.university if requirement else None  # Get university through relationship
        
        course_data = {
            'id': course.id,
            'course_name': course.course_name,
            'university_name': university.university_name if university else None,
            'abbrv': university.abbrv if university else None,  # Get from university object
            'utme_requirements': requirement.utme_requirements if requirement else None,
            'direct_entry_requirements': requirement.direct_entry_requirements if requirement else None,
            'subjects': requirement.subject_requirement.subjects if requirement and requirement.subject_requirement else None,
            'university_id': university.id if university else None,
        }
        return jsonify(course_data), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching course details: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching course details.'}), 500

@bp.route('/reply_comment', methods=['POST'])
@login_required
def reply_comment():
    data = request.get_json()
    raw_content = data.get("reply", "").strip()
    parent_id = data.get("parent_comment_id", None)

    if not raw_content:
        return jsonify({"success": False, "message": "Reply content cannot be empty."}), 400

    if not parent_id:
        return jsonify({"success": False, "message": "Invalid parent comment."}), 400

    content = bleach.clean(raw_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)

    try:
        parent_comment = Comment.query.get_or_404(parent_id)
        reply_comment = Comment(content=content, user_id=current_user.id, parent_id=parent_id)
        db.session.add(reply_comment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Reply added successfully.",
            "reply": {
                "id": reply_comment.id,
                "content": reply_comment.content,
                "user_id": reply_comment.user_id,
                "username": current_user.username,
                "date_posted": reply_comment.date_posted.strftime('%B %d, %Y at %H:%M'),
                "likes": 0,
                "dislikes": 0,
                "score": current_user.score,
                "is_admin": current_user.is_admin
            }
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding reply: {str(e)}")
        return jsonify({"success": False, "message": "Error adding reply."}), 500

@bp.route('/comments_with_replies', methods=['GET'])
def comments_with_replies():
    try:
        # Get parent comments ordered by newest first
        comments = (Comment.query
            .filter_by(parent_id=None)
            .order_by(Comment.date_posted.desc())  # This sorts main comments newest first
            .options(joinedload('replies').order_by(Comment.date_posted.asc()))  # This sorts replies oldest first
            .options(joinedload('author'))
            .all())

        comments_data = []
        for comment in comments:
            # No need for Python sorting since we're using SQL ordering
            replies = [{
                "id": reply.id,
                "content": reply.content,
                "user_id": reply.user_id,
                "username": reply.author.username,
                "date_posted": reply.date_posted.strftime('%B %d, %Y at %H:%M'),
                "likes": reply.likes,
                "dislikes": reply.dislikes,
                "score": reply.author.score,
                "is_admin": reply.author.is_admin
            } for reply in comment.replies]  # replies will already be sorted
            
            comments_data.append({
                "id": comment.id,
                "content": comment.content,
                "user_id": comment.user_id,
                "username": comment.author.username,
                "date_posted": comment.date_posted.strftime('%B %d, %Y at %H:%M'),
                "likes": comment.likes,
                "dislikes": comment.dislikes,
                "score": comment.author.score,
                "is_admin": comment.author.is_admin,
                "reply_count": len(replies),
                "replies": replies
            })

        return jsonify(comments_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching comments with replies: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve comments with replies",
            "message": str(e) if current_app.debug else "An error occurred while retrieving comments."
        }), 500
        
def get_recommendations():
    try:
        params = validate_recommendation_params(request.args)
        
        # Updated query to properly join and load requirements
        base_query = (db.session.query(Course, University, CourseRequirement)
            .join(CourseRequirement, Course.id == CourseRequirement.course_id)
            .join(University, University.id == CourseRequirement.university_id)
            .options(joinedload(Course.requirements)
                    .joinedload(CourseRequirement.subject_requirement)))

        # Apply filters
        if params['location']:
            base_query = base_query.filter(University.state == params['location'])
        
        if params['programme_type']:
            base_query = base_query.filter(University.program_type.in_(params['programme_type']))

        paginated_results = paginate_query(base_query, page=params['page'], per_page=params['per_page'])
        
        return jsonify({
            'items': [{
                'id': course.id,
                'course_name': course.course_name,
                'university_name': university.university_name,
                'state': university.state,
                'program_type': university.program_type,
                'utme_requirements': requirement.utme_requirements if requirement else None,
                'direct_entry_requirements': requirement.direct_entry_requirements if requirement else None,
                'subjects': requirement.subject_requirement.subjects if requirement and requirement.subject_requirement else None
            } for course, university, requirement in paginated_results.items],
            'pagination': {
                'page': paginated_results.page,
                'per_page': paginated_results.per_page,
                'total_pages': paginated_results.pages,
                'total_items': paginated_results.total
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error in recommendations: {str(e)}")
        return jsonify({
            'error': 'An error occurred while fetching recommendations',
            'details': str(e) if current_app.debug else None
        }), 500
        
def paginate_query(query, page=1, per_page=50):
    """Helper function to paginate query results"""
    try:
        return query.paginate(page=page, per_page=per_page, error_out=False)
    except Exception as e:
        raise ValueError(f"Pagination error: {str(e)}")


def validate_recommendation_params(params):
    """Validate and clean recommendation parameters"""
    try:
        validated = {
            'location': params.get('location', '').strip(),
            'programme_type': [p.strip() for p in params.get('programme_type', '').split(',') if p.strip()],
            'selected_institutions': [i.strip() for i in params.get('institutions', '').split(',') if i.strip()],
            'page': int(params.get('page', 1)),
            'per_page': min(int(params.get('per_page', 50)), 100)  # Limit maximum items per page
        }
        return validated
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid parameter format: {str(e)}")

def format_recommendation_response(paginated_results):
    return {
        'items': [{
            'id': course.id,
            'course_name': course.course_name,
            'university_name': university.university_name,
            'state': university.state,
            'program_type': university.program_type,
            'utme_requirements': requirement.utme_requirements if requirement else None,
            'direct_entry_requirements': requirement.direct_entry_requirements if requirement else None,
            'subjects': requirement.subject_requirement.subjects if requirement and requirement.subject_requirement else None
        } for course, university, requirement in paginated_results.items],
        'pagination': {
            'page': paginated_results.page,
            'per_page': paginated_results.per_page,
            'total_pages': paginated_results.pages,
            'total_items': paginated_results.total
        }
    }