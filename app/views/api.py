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

bp = Blueprint('api', __name__)

@bp.route('/api/locations')
def get_locations():
    try:
        locations = University.get_all_states()
        current_app.logger.info(f"Retrieved {len(locations)} locations")
        return jsonify(locations)
    except Exception as e:
        current_app.logger.error(f"Error retrieving locations: {str(e)}")
        return jsonify({"error": "Failed to retrieve locations"}), 500

@bp.route('/api/programme_types', methods=['GET'])
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

@bp.route('/api/universities', methods=['GET'])
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

@bp.route('/api/courses', methods=['GET'])
def get_courses():
    state = request.args.get('state')
    programme_type = request.args.get('programme_type')
    university = request.args.get('university')
    
    query = db.session.query(Course).join(University)
    if state:
        query = query.filter(University.state == state)
    if programme_type:
        if programme_type in Config.PROGRAMME_GROUPS:
            programme_types = Config.PROGRAMME_GROUPS[programme_type]
            query = query.filter(University.program_type.in_(programme_types))
        elif programme_type == "ALL_INSTITUTION_TYPES":
            pass
        else:
            query = query.filter(University.program_type == programme_type)
    if university:
        query = query.filter(University.university_name == university)
        
    courses = query.order_by(Course.course_name).all()
    return jsonify([{
        "id": course.id,
        "course_name": course.course_name,
        "university_name": course.university_name,
        "abbrv": course.abbrv,
        "direct_entry_requirements": course.direct_entry_requirements,
        "utme_requirements": course.utme_requirements,
        "subjects": course.subjects,
    } for course in courses])

@bp.route('/api/institution/<int:uni_id>')
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
            "selected_course": selected_course,
            "courses": [{
                "id": course.id,
                "course_name": course.course_name,
                "utme_requirements": course.utme_requirements or "N/A",
                "subjects": course.subjects or "N/A",
                "direct_entry_requirements": course.direct_entry_requirements or "N/A",
                "abbrv": course.abbrv or "N/A",
            } for course in courses]
        }

        return jsonify(response_data), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_institution_details: {str(e)}")
        return jsonify({"error": "An error occurred while fetching institution details."}), 500

@bp.route('/api/bookmark', methods=['POST'])
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

@bp.route('/api/user_bookmarks', methods=['GET'])
@login_required
def get_user_bookmarks():
    bookmarks = [bookmark.university_id for bookmark in current_user.bookmarks]
    return jsonify(bookmarks)


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

@bp.route('/api/vote/<int:comment_id>/<vote_type>', methods=['POST'])
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
    
@bp.route('/api/user_votes', methods=['GET'])
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