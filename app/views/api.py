# app/views/api.py

from flask import Blueprint, jsonify, request, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from ..models.university import University, Course, ProgrammeType, State
from ..models.interaction import Comment, Vote, Bookmark
from ..models.requirement import CourseRequirement
from ..models.user import User
from ..extensions import db
from ..config import Config
from ..utils.decorators import admin_required
import bleach
from sqlalchemy import distinct, text, func
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
from ..forms.comment import CommentForm
import threading
from typing import Dict, List
from collections import defaultdict
import logging

# Get the query timing logger
timing_logger = logging.getLogger('query_timing')
sql_logger = logging.getLogger('sqlalchemy.engine')

bp = Blueprint('api', __name__, url_prefix='/api')

# Define allowed tags and attributes for sanitization
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title']
}

def log_connection_info(conn, stage: str):
    """Helper to log connection info state"""
    thread_id = threading.get_ident()
    timing_logger.debug(
        f"[{stage}] Thread: {thread_id} | "
        f"Connection ID: {id(conn)} | "
        f"Info: {dict(conn.info)} | "
        f"Has query_start_time: {'query_start_time' in conn.info}"
    )

def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    thread_id = threading.get_ident()
    timing_logger.debug(f"[BEFORE] Entering handler - Thread: {thread_id}")
    
    if not hasattr(conn.info, 'query_start_time'):
        conn.info['query_start_time'] = []
        timing_logger.debug(f"[BEFORE] Initialized query_start_time list - Thread: {thread_id}")
    
    conn.info['query_start_time'].append(time.time())
    timing_logger.debug(
        f"[BEFORE] Added timestamp - Thread: {thread_id} | "
        f"List length: {len(conn.info['query_start_time'])}"
    )

def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    thread_id = threading.get_ident()
    timing_logger.debug(f"[AFTER] Entering handler - Thread: {thread_id}")
    
    try:
        if 'query_start_time' in conn.info and conn.info['query_start_time']:
            start_time = conn.info['query_start_time'].pop(-1)
            total = time.time() - start_time
            timing_logger.debug(
                f"[AFTER] Query timing successful - Thread: {thread_id} | "
                f"Total time: {total} | "
                f"Remaining timestamps: {len(conn.info['query_start_time'])}"
            )
        else:
            timing_logger.warning(
                f"[AFTER] No query_start_time available - Thread: {thread_id} | "
                f"Connection info: {dict(conn.info)}"
            )
            total = 0
    except (KeyError, IndexError) as e:
        timing_logger.error(
            f"[AFTER] Error processing query time - Thread: {thread_id} | "
            f"Error: {str(e)} | "
            f"Connection info: {dict(conn.info)}"
        )
        total = 0

# Register event listeners only once at the module level
event.listen(Engine, "before_cursor_execute", before_cursor_execute)
event.listen(Engine, "after_cursor_execute", after_cursor_execute)

@bp.route('/locations')
def get_locations():
    try:
        current_app.logger.debug("Starting location query")
        
        # Query all states
        states = db.session.query(State).order_by(State.name).all()
        current_app.logger.debug(f"Raw states from database: {states}")

        # Process states
        locations = []
        for state in states:
            if hasattr(state, 'name') and state.name:
                locations.append(state.name)
            else:
                current_app.logger.warning(f"Invalid state object: {state}")

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

@bp.route('/featured-institutions')
def get_featured_institutions():
    try:
        thread_id = threading.get_ident()
        current_app.logger.debug(f"[FEATURED] Starting featured institutions query - Thread: {thread_id}")
        
        # Query featured institutions
        featured = University.query\
            .filter_by(is_featured=True)\
            .join(State, University.state_id == State.id)\
            .join(ProgrammeType, University.programme_type_id == ProgrammeType.id)\
            .options(
                joinedload(University.state_info),
                joinedload(University.programme_type_info)
            )\
            .order_by(func.random())\
            .limit(6)
            
        current_app.logger.debug(f"[FEATURED] Executing query - Thread: {thread_id}")
        
        results = featured.all()
        
        current_app.logger.debug(f"[FEATURED] Query completed - Thread: {thread_id} | Results: {len(results)}")
        
        # Transform to response format
        institutions = []
        for inst in results:
            try:
                institution = {
                    'id': inst.id,
                    'name': inst.university_name,
                    'state': inst.state_info.name if inst.state_info else 'Unknown',
                    'type': inst.programme_type_info.name if inst.programme_type_info else 'Unknown',
                    'courses_count': len(inst.courses) if hasattr(inst, 'courses') else 0
                }
                institutions.append(institution)
            except Exception as inst_error:
                current_app.logger.error(f"Error processing institution {inst.id}: {str(inst_error)}")
                continue
        
        return jsonify({
            'status': 'success',
            'institutions': institutions
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching featured institutions: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch featured institutions',
            'details': str(e) if current_app.debug else None
        }), 500

@bp.route('/programme-types')
def get_programme_types():
    """Get all programme types"""
    try:
        programme_types = db.session.query(
            ProgrammeType.name,
            ProgrammeType.category,
            ProgrammeType.institution_type
        ).order_by(ProgrammeType.name).all()
        
        if not programme_types:
            current_app.logger.warning("No programme types found in database")
            return jsonify({
                "status": "error",
                "message": "No programme types available"
            }), 404
            
        types = [{
            'name': pt.name,
            'category': pt.category,
            'institution_type': pt.institution_type
        } for pt in programme_types]
        current_app.logger.info(f"Retrieved {len(types)} programme types")
        
        return jsonify({
            "status": "success",
            "data": types
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving programme types: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve programme types",
            "details": str(e) if current_app.debug else None
        }), 500

@bp.route('/programme-types/<state>')
def get_programme_types_by_state(state):
    """Get programme types available in a specific state"""
    try:
        # Validate state parameter
        state_obj = db.session.query(State).filter(func.lower(State.name) == func.lower(state)).first()
        if not state_obj:
            current_app.logger.warning(f"Invalid state requested: {state}")
            return jsonify({
                "status": "error",
                "message": f"Invalid state: {state}"
            }), 404
            
        # Query programme types for universities in the state
        programme_types = db.session.query(
            ProgrammeType.name,
            ProgrammeType.category,
            ProgrammeType.institution_type
        ).join(
            University, 
            University.programme_type_id == ProgrammeType.id
        ).filter(
            University.state_id == state_obj.id
        ).distinct().order_by(ProgrammeType.name).all()
            
        if not programme_types:
            current_app.logger.warning(f"No programme types found for state: {state}")
            return jsonify({
                "status": "error",
                "message": f"No programme types available for {state}"
            }), 404
            
        types = [{
            'name': pt.name,
            'category': pt.category,
            'institution_type': pt.institution_type
        } for pt in programme_types]
        current_app.logger.info(f"Retrieved {len(types)} programme types for {state}")
        
        return jsonify({
            "status": "success",
            "data": types
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving programme types for {state}: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve programme types for {state}",
            "details": str(e) if current_app.debug else None
        }), 500

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

@bp.route('/bookmark', methods=['POST'])
@login_required
def add_bookmark():
    data = request.get_json()
    university_id = data.get('university_id')

    if not university_id:
        return jsonify({"success": False, "message": "Invalid university."}), 400

    try:
        with atomic_transaction():
            existing_bookmark = Bookmark.query.filter_by(
                user_id=current_user.id,
                university_id=university_id
            ).first()
            
            if existing_bookmark:
                return jsonify({"success": True, "message": "Already bookmarked"}), 200

            bookmark = Bookmark(user_id=current_user.id, university_id=university_id)
            db.session.add(bookmark)
            
        return jsonify({
            "success": True,
            "message": "Institution bookmarked successfully."
        }), 200
    except SQLAlchemyError as e:
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
        with atomic_transaction():
            bookmark = Bookmark.query.filter_by(
                user_id=current_user.id,
                university_id=university_id
            ).first()
            
            if bookmark:
                current_app.logger.info(f"Found bookmark to remove: {bookmark.id}")
                db.session.delete(bookmark)
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
        current_app.logger.error(f"Error removing bookmark: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An error occurred while removing the bookmark."
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

@bp.route('/search_institutions', methods=['GET'])
def search_institutions():
    try:
        search_term = request.args.get('search', '').lower()
        state = request.args.get('state')
        types = request.args.getlist('type')
        program_types = request.args.getlist('program')
        page = request.args.get('page', 1, type=int)
        per_page = 12

        query = University.query\
            .join(State, University.state_id == State.id)\
            .join(ProgrammeType, University.programme_type_id == ProgrammeType.id)\
            .options(
                joinedload(University.state_info),
                joinedload(University.programme_type_info)
            )

        if search_term:
            query = query.filter(
                db.or_(
                    University.university_name.ilike(f'%{search_term}%'),
                    State.name.ilike(f'%{search_term}%'),
                    ProgrammeType.name.ilike(f'%{search_term}%')
                )
            )

        if state:
            query = query.filter(State.name == state)
        if types:
            query = query.filter(ProgrammeType.name.in_(types))
        if program_types:
            query = query.filter(ProgrammeType.category.in_(program_types))

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

@bp.route('/reply_comment', methods=['POST'])
@login_required
def reply_comment():
    try:
        # Get JSON data from the request
        data = request.get_json()
        parent_comment_id = data.get('parent_comment_id')
        reply_text = data.get('reply')
        parent_level = data.get('parent_level', 0)

        # Validate input
        if not parent_comment_id or not reply_text:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # Fetch the parent comment
        parent_comment = Comment.query.get_or_404(parent_comment_id)

        # Check reply depth (optional, based on your app's rules)
        if int(parent_level) >= 3:
            return jsonify({"success": False, "message": "Maximum reply depth reached"}), 400

        # Create a new reply
        new_reply = Comment(
            content=reply_text,
            user_id=current_user.id,
            parent_id=parent_comment_id,
            university_id=parent_comment.university_id  # Inherit from parent comment
        )

        # Save to database
        db.session.add(new_reply)
        db.session.commit()

        # Return success response with reply details
        return jsonify({
            "success": True,
            "message": "Reply added successfully",
            "reply": {
                "id": new_reply.id,
                "content": new_reply.content,
                "username": current_user.username,
                "date_posted": new_reply.date_posted.strftime('%Y-%m-%d %H:%M:%S'),
                "likes": 0,
                "dislikes": 0,
                "is_admin": current_user.is_admin
            }
        }), 201

    except Exception as e:
        # Roll back on error
        db.session.rollback()
        current_app.logger.error(f"Error adding reply: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while adding your reply"}), 500

@bp.route('/vote/<int:comment_id>/<vote_type>', methods=['POST'])
@login_required
def vote(comment_id, vote_type):
    if vote_type not in ['like', 'dislike']:
        return jsonify({'success': False, 'message': 'Invalid vote type'}), 400

    try:
        with atomic_transaction():
            comment = Comment.query.get_or_404(comment_id)
            comment_author = User.query.get_or_404(comment.user_id)
            existing_vote = Vote.query.filter_by(
                user_id=current_user.id,
                comment_id=comment_id
            ).first()

            if existing_vote:
                if existing_vote.vote_type == vote_type:
                    if vote_type == 'like':
                        comment.likes -= 1
                        comment_author.score -= 1
                    else:
                        comment.dislikes -= 1
                        comment_author.score += 1
                    db.session.delete(existing_vote)
                    current_vote = None
                else:
                    if vote_type == 'like':
                        comment.likes += 1
                        comment.dislikes -= 1
                        comment_author.score += 2
                    else:
                        comment.likes -= 1
                        comment.dislikes += 1
                        comment_author.score -= 2
                    existing_vote.vote_type = vote_type
                    current_vote = vote_type
            else:
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

@bp.route('/institution/<int:id>/comment', methods=['POST'])
@login_required
def add_institution_comment(id):
    """Add a comment to an institution"""
    try:
        # Handle form submission
        if request.form:
            form = CommentForm()
            if form.validate_on_submit():
                content = form.content.data
                parent_id = request.form.get('parent_id')
                
                comment = Comment(
                    content=content,
                    user_id=current_user.id,
                    university_id=id,
                    parent_id=parent_id if parent_id else None
                )
                
                db.session.add(comment)
                db.session.commit()
                
                flash('Comment added successfully', 'success')
                return redirect(url_for('university.institution_details', id=id))
            else:
                flash('Invalid comment data', 'danger')
                return redirect(url_for('university.institution_details', id=id))
        
        # Handle JSON submission
        content = request.json.get('content', '').strip() if request.is_json else None
        if content:
            with db.session.begin_nested():
                comment = Comment(
                    content=content,
                    author=current_user,
                    university_id=id
                )
                db.session.add(comment)
            
            db.session.commit()
            current_app.logger.info(f'Added comment to institution {id} by user {current_user.id}')
            
            return jsonify({
                'message': 'Comment added successfully',
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'author': comment.author.username,
                    'date_posted': comment.date_posted.strftime('%Y-%m-%d %H:%M:%S')
                }
            }), 201
            
        return jsonify({'error': 'Invalid request format'}), 400
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f'Database error adding comment to institution {id}: {str(e)}')
        if request.is_json:
            return jsonify({'error': 'Failed to add comment'}), 500
        flash('An error occurred while adding your comment', 'danger')
        return redirect(url_for('university.institution_details', id=id))
        
    except Exception as e:
        current_app.logger.error(f'Unexpected error adding comment to institution {id}: {str(e)}')
        if request.is_json:
            return jsonify({'error': 'An unexpected error occurred'}), 500
        flash('An error occurred while adding your comment', 'danger')
        return redirect(url_for('university.institution_details', id=id))

@bp.route('/api/institution/<int:institution_id>/comments', methods=['GET'])
def get_institution_comments(institution_id):
    try:
        institution = University.query.get_or_404(institution_id)
        comments = Comment.query\
            .filter_by(university_id=institution_id, parent_id=None)\
            .order_by(Comment.date_posted.desc())\
            .all()
            
        return jsonify({
            'comments': [{
                'id': comment.id,
                'content': comment.content,
                'author': comment.author.username,
                'date_posted': comment.date_posted.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': comment.user_id
            } for comment in comments]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error fetching comments for institution {institution_id}: {str(e)}')
        return jsonify({'error': 'Failed to fetch comments'}), 500

