# app/views/api.py

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from ..models.university import University, Course, CourseRequirement, ProgrammeType, State
from ..models.interaction import Bookmark, Comment, Vote
from ..models.user import User
from ..extensions import db
from ..config import Config
from ..utils.decorators import admin_required
import bleach
from sqlalchemy import distinct, text
from sqlalchemy import func
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

bp = Blueprint('api', __name__)

# Define allowed tags and attributes for sanitization
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title']
}

@bp.route('/locations')
def get_locations():
    try:
        # Add debug logging for query
        current_app.logger.debug("Starting location query")
        
        # Enable SQLAlchemy query logging
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
            current_app.logger.debug("SQL: %s", statement)

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            current_app.logger.debug("Total Time: %f", total)

        # Query all states
        try:
            states = db.session.query(State).order_by(State.name).all()
            current_app.logger.debug(f"Raw states from database: {states}")
        except Exception as db_error:
            current_app.logger.error(f"Database query error: {str(db_error)}")
            raise

        # Process states
        try:
            locations = []
            for state in states:
                current_app.logger.debug(f"Processing state: {state}")
                if hasattr(state, 'name') and state.name:
                    locations.append(state.name)
                else:
                    current_app.logger.warning(f"Invalid state object: {state}")
        except Exception as proc_error:
            current_app.logger.error(f"State processing error: {str(proc_error)}")
            raise

        current_app.logger.debug(f"Processed locations: {locations}")
        
        if locations:
            locations.insert(0, "ALL")
            current_app.logger.info(f"Retrieved {len(locations)} locations including ALL option")
            return jsonify(locations)
        else:
            current_app.logger.warning("No states found in database")
            return jsonify({
                "status": "error",
                "message": "No states available in the database"
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error retrieving locations: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve locations",
            "details": str(e) if current_app.debug else None
        }), 500

@bp.route('/programme_types', methods=['GET'])
def get_all_programme_types():
    """Get all programme types when no state is selected"""
    try:
        current_app.logger.debug("Fetching all programme types")
        
        # Query directly from ProgrammeType table
        programme_types = db.session.query(
            ProgrammeType.name,
            ProgrammeType.category,
            ProgrammeType.institution_type
        ).order_by(ProgrammeType.name).all()
        
        current_app.logger.debug(f"Found {len(programme_types)} programme types")
        
        # Format response
        types_list = [{
            'name': pt[0],
            'category': pt[1],
            'institution_type': pt[2]
        } for pt in programme_types]
        
        return jsonify({
            'status': 'success',
            'data': types_list
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in get_all_programme_types: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"Database error: {str(e)}"
        }), 500

@bp.route('/programme-types/<state>', methods=['GET'])
def get_programme_types(state):
    """Get programme types for institutions in a specific state"""
    try:
        # Base query for programme types
        query = db.session.query(
            ProgrammeType.name,
            ProgrammeType.category,
            ProgrammeType.institution_type
        )
        
        if state != 'ALL':
            # Join with University and State tables only if filtering by state
            query = query.join(
                University, 
                University.programme_type_id == ProgrammeType.id
            ).join(
                State, 
                University.state_id == State.id
            ).filter(State.name == state)
        
        programme_types = query.distinct().order_by(ProgrammeType.name).all()
        
        # Format response
        types_list = [{
            'name': pt[0],
            'category': pt[1],
            'institution_type': pt[2]
        } for pt in programme_types]
        
        return jsonify({
            'status': 'success',
            'data': types_list
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in get_programme_types: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/universities', methods=['GET'])
def get_universities():
    state = request.args.get('state')
    try:
        query = (db.session.query(
            University.university_name,
            State.name.label('state'),
            ProgrammeType.name.label('program_type')
        )
        .join(State, University.state_id == State.id)
        .join(ProgrammeType, University.programme_type_id == ProgrammeType.id))
        
        if state:
            query = query.filter(State.name == state)
            
        universities = query.all()
        
        return jsonify([{
            "university_name": uni.university_name,
            "state": uni.state,
            "program_type": uni.program_type,
        } for uni in universities])
    except Exception as e:
        current_app.logger.error(f"Error retrieving universities: {str(e)}")
        return jsonify({"error": "Failed to retrieve universities."}), 500

@bp.route('/courses', methods=['POST'])
def get_courses():
    try:
        # Add CSRF protection
        if request.method == "POST":
            csrf_token = request.headers.get('X-CSRF-TOKEN')
            if not csrf_token:
                current_app.logger.warning("CSRF token missing in request")
                return jsonify({
                    'status': 'error',
                    'message': 'CSRF token is missing'
                }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        state = data.get('state')
        programme_types = data.get('programme_type', '').split(',')
        load_all = data.get('load_all', False)
        
        current_app.logger.debug(f"Getting courses for state: {state}, types: {programme_types}")
        
        # Build base query
        query = db.session.query(
            Course.id,
            Course.course_name,
            Course.code,
            func.count(distinct(University.id)).label('institution_count')
        ).join(
            CourseRequirement,
            Course.id == CourseRequirement.course_id
        ).join(
            University,
            CourseRequirement.university_id == University.id
        ).join(
            State,
            University.state_id == State.id
        ).join(
            ProgrammeType,
            University.programme_type_id == ProgrammeType.id
        )
        
        # Apply filters
        if state and state != 'ALL':
            query = query.filter(State.name == state)
        
        if programme_types and programme_types[0]:
            query = query.filter(ProgrammeType.name.in_(programme_types))
        
        # Group and order
        query = query.group_by(
            Course.id,
            Course.course_name,
            Course.code
        ).order_by(Course.course_name)
        
        # Execute query
        courses = query.all()
        
        # Format response
        response_data = [{
            'id': course.id,
            'course_name': course.course_name,
            'code': course.code,
            'institution_count': course.institution_count
        } for course in courses]
        
        current_app.logger.info(f"Found {len(response_data)} courses")
        
        return jsonify({
            'status': 'success',
            'courses': response_data,
            'total': len(response_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting courses: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

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

@bp.route('/institution/<int:id>')
def get_institution_details(id):
    try:
        # Get query parameters
        selected_course = request.args.get('selected_course')
        
        # Query university with eager loading of relationships
        university = University.query\
            .options(joinedload(University.state_info))\
            .options(joinedload(University.programme_type_info))\
            .options(joinedload(University.courses))\
            .get_or_404(id)
        
        # Get requirements with proper joins
        requirements = CourseRequirement.query\
            .filter_by(university_id=id)\
            .options(joinedload(CourseRequirement.course))\
            .all()
        
        current_app.logger.info(f"Found {len(requirements)} requirements for university {id}")
        
        # Create requirements lookup
        req_lookup = {req.course_id: req for req in requirements}
        
        # Get courses with requirements
        courses = Course.query\
            .join(CourseRequirement)\
            .filter(CourseRequirement.university_id == id)\
            .order_by(Course.course_name)\
            .all()
        
        current_app.logger.info(f"Found {len(courses)} courses for university {id}")
        
        # Format response
        response_data = {
            "id": university.id,
            "university_name": university.university_name,
            "state": university.state_info.name,  # Use state_info relationship
            "program_type": university.programme_type_info.name,  # Use programme_type_info relationship
            "website": university.website,
            "established": university.established,
            "abbrv": university.abbrv,
            "selected_course": selected_course,
            "courses": []
        }
        
        # Add course data
        for course in courses:
            req = req_lookup.get(course.id)
            course_data = {
                "id": course.id,
                "course_name": course.course_name,
                "utme_requirements": req.utme_requirements if req else None,
                "direct_entry_requirements": req.direct_entry_requirements if req else None,
                "subjects": req.subject_requirement.subjects if req and req.subject_requirement else None
            }
            response_data["courses"].append(course_data)
        
        return jsonify(response_data)
        
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
            # Using a subquery to get all universities for each course
            courses = (db.session.query(
                Course.id,
                Course.course_name,
                func.array_agg(
                    func.json_build_object(
                        'university_name', University.university_name,
                        'abbrv', University.abbrv
                    )
                ).label('universities')
            )
            .join(CourseRequirement, Course.id == CourseRequirement.course_id)
            .join(University, University.id == CourseRequirement.university_id)
            .filter(
                db.or_(
                    Course.course_name.ilike(f'%{query}%'),
                    University.abbrv.ilike(f'%{query}%')
                )
            )
            .group_by(Course.id, Course.course_name)
            .order_by(Course.course_name)
            .all())
        else:
            return jsonify({'courses': []})

        courses_data = [{
            'id': course.id,
            'course_name': course.course_name,
            'universities': [
                {
                    'university_name': uni['university_name'],
                    'abbrv': uni['abbrv']
                } for uni in course.universities
            ]
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

@bp.route('/admin/search_universities')
@login_required
@admin_required
def search_universities():
    query = request.args.get('query', '').strip()
    try:
        universities = University.query.filter(
            db.or_(
                University.university_name.ilike(f'%{query}%'),
                University.abbrv.ilike(f'%{query}%')
            )
        ).order_by(University.university_name).all()
        
        return jsonify({
            'universities': [{
                'id': uni.id,
                'university_name': uni.university_name,
                'abbrv': uni.abbrv,
                'program_type': uni.program_type
            } for uni in universities]
        })
    except Exception as e:
        current_app.logger.error(f"Error searching universities: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/add_university_to_course', methods=['POST'])
@login_required
@admin_required
def add_university_to_course():
    data = request.get_json()
    course_id = data.get('course_id')
    university_id = data.get('university_id')
    
    try:
        requirement = CourseRequirement(
            course_id=course_id,
            university_id=university_id
        )
        db.session.add(requirement)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding university to course: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/remove_university_from_course', methods=['POST'])
@login_required
@admin_required
def remove_university_from_course():
    data = request.get_json()
    course_id = data.get('course_id')
    university_id = data.get('university_id')
    
    try:
        requirement = CourseRequirement.query.filter_by(
            course_id=course_id,
            university_id=university_id
        ).first()
        if requirement:
            db.session.delete(requirement)
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing university from course: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/search_institutions', methods=['GET'])
def search_institutions():
    try:
        search_term = request.args.get('search', '').lower()
        state = request.args.get('state')
        types = request.args.getlist('type')
        program_types = request.args.getlist('program')
        page = request.args.get('page', 1, type=int)
        per_page = 12  # Match the main route's pagination

        # Base query with joins
        query = University.query\
            .join(State, University.state_id == State.id)\
            .join(ProgrammeType, University.programme_type_id == ProgrammeType.id)\
            .options(
                joinedload(University.state_info),
                joinedload(University.programme_type_info)
            )

        # Apply search filter
        if search_term:
            query = query.filter(
                db.or_(
                    University.university_name.ilike(f'%{search_term}%'),
                    State.name.ilike(f'%{search_term}%'),
                    ProgrammeType.name.ilike(f'%{search_term}%')
                )
            )

        # Apply additional filters
        if state:
            query = query.filter(State.name == state)
        if types:
            query = query.filter(ProgrammeType.name.in_(types))
        if program_types:
            query = query.filter(ProgrammeType.category.in_(program_types))

        # Paginate results
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'status': 'success',
            'count': pagination.total,
            'institutions': [{
                'id': inst.id,
                'name': inst.university_name,
                'state': inst.state_info.name,
                'type': inst.programme_type_info.name,
                'courses_count': len(inst.courses)
            } for inst in pagination.items],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'total': pagination.total
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error in search_institutions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while searching institutions'
        }), 500