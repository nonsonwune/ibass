# app/views/api.py

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from contextlib import contextmanager
from sqlalchemy import exc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from ..models.university import University, Course
from ..models.interaction import Bookmark, Comment, Vote
from ..models.user import User
from ..extensions import db
from ..config import Config
from ..utils.decorators import admin_required

bp = Blueprint('api', __name__)

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
    if state:
        universities = University.query.filter_by(state=state).all()
    else:
        universities = University.query.all()
    return jsonify([{
        "university_name": uni.university_name,
        "state": uni.state,
        "program_type": uni.program_type,
    } for uni in universities])

@bp.route('/courses', methods=['GET'])
def get_courses():
    state = request.args.get('state')
    programme_types = request.args.get('programme_type', '').split(',')
    university = request.args.get('university')
    
    try:
        # Start with base query
        query = db.session.query(Course).join(University)
        
        # Filter by state only if not "ALL"
        if state and state != "ALL":
            query = query.filter(University.state == state)
        
        # Handle multiple programme types
        if programme_types and programme_types[0]:  # Check if not empty string
            expanded_types = []
            for ptype in programme_types:
                if ptype in Config.PROGRAMME_GROUPS:
                    expanded_types.extend(Config.PROGRAMME_GROUPS[ptype])
                else:
                    expanded_types.append(ptype)
            
            query = query.filter(University.program_type.in_(expanded_types))
        
        if university:
            query = query.filter(University.university_name == university)
            
        courses = query.order_by(Course.course_name).all()
        
        # Add "All Courses" option at the beginning of the response
        response_data = [{
            "id": 0,  # Special ID for "All Courses"
            "course_name": "ALL",
            "university_name": None,
            "state": None,
            "program_type": None,
            "abbrv": None,
            "direct_entry_requirements": None,
            "utme_requirements": None,
            "subjects": None,
        }]
        
        # Add actual courses
        response_data.extend([{
            "id": course.id,
            "course_name": course.course_name,
            "university_name": course.university.university_name,
            "state": course.university.state,
            "program_type": course.university.program_type,
            "abbrv": course.university.abbrv,
            "direct_entry_requirements": course.direct_entry_requirements,
            "utme_requirements": course.utme_requirements,
            "subjects": course.subjects,
        } for course in courses])
        
        current_app.logger.info(f"Found {len(response_data)-1} courses for state: {state}, types: {programme_types}")
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving courses: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve courses",
            "message": str(e)
        }), 500

@bp.route('/institution/<int:uni_id>')
def get_institution_details(uni_id):
    try:
        selected_course = request.args.get('selected_course')
        university = University.query.get_or_404(uni_id)
        courses = Course.query.filter_by(university_name=university.university_name).all()

        response_data = {
            "id": university.id,
            "university_name": university.university_name,
            "state": university.state,
            "program_type": university.program_type,
            "website": university.website,
            "established": university.established,
            "abbrv": university.abbrv,  # Added this line
            "selected_course": selected_course,
            "courses": [{
                "id": course.id,
                "course_name": course.course_name,
                "utme_requirements": course.utme_requirements or "N/A",
                "subjects": course.subjects or "N/A",
                "direct_entry_requirements": course.direct_entry_requirements or "N/A",
            } for course in courses]
        }

        return jsonify(response_data), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_institution_details: {str(e)}")
        return jsonify({"error": "An error occurred while fetching institution details."}), 500

@bp.route('/bookmark', methods=['POST'])
@login_required
def add_bookmark():
    data = request.get_json()
    university_id = data.get('university_id')

    if not university_id:
        return jsonify({"success": False, "message": "Invalid university."}), 400

    existing_bookmark = Bookmark.query.filter_by(
        user_id=current_user.id,
        university_id=university_id
    ).first()
    
    if existing_bookmark:
        return jsonify({"success": True, "message": "Already bookmarked"}), 200

    try:
        bookmark = Bookmark(user_id=current_user.id, university_id=university_id)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Institution bookmarked successfully."
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
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
    try:
        bookmark = Bookmark.query.filter_by(
            user_id=current_user.id,
            university_id=university_id
        ).first()
        
        if bookmark:
            db.session.delete(bookmark)
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "Bookmark removed successfully."
            }), 200
        else:
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

        courses_query = Course.query.join(University).filter(
            (Course.course_name.ilike(f"%{query_text}%"))
            | (University.abbrv.ilike(f"%{query_text}%"))
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
                    "university_name": course.university_name,
                    "abbrv": course.abbrv,
                    "direct_entry_requirements": course.direct_entry_requirements,
                    "utme_requirements": course.utme_requirements,
                    "subjects": course.subjects,
                }
                for course in courses
            ],
        })
    except Exception as e:
        current_app.logger.error(f"Error in search: {str(e)}")
        return jsonify({
            "error": "An error occurred while processing your search. Please try again."
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
        course = Course.query.get_or_404(course_id)
        university = University.query.filter_by(university_name=course.university_name).first()
        course_data = {
            'id': course.id,
            'course_name': course.course_name,
            'university_name': course.university_name,
            'abbrv': course.abbrv,
            'utme_requirements': course.utme_requirements,
            'direct_entry_requirements': course.direct_entry_requirements,
            'subjects': course.subjects,
            'university_id': university.id if university else None,
        }
        return jsonify(course_data), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching course details: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching course details.'}), 500