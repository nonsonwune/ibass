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

@bp.route('/api/vote/<int:comment_id>/<string:vote_type>', methods=['POST'])
@login_required
def vote(comment_id, vote_type):
    if vote_type not in ['like', 'dislike']:
        return jsonify({'success': False, 'message': 'Invalid vote type'}), 400

    try:
        with atomic_transaction():
            # Get comment with FOR UPDATE and eagerly load author
            comment = db.session.query(Comment).options(
                joinedload(Comment.author)
            ).filter_by(id=comment_id).with_for_update().first()

            if not comment:
                return jsonify({'success': False, 'message': 'Comment not found'}), 404

            # Get existing vote with FOR UPDATE
            existing_vote = db.session.query(Vote).filter_by(
                user_id=current_user.id,
                comment_id=comment_id
            ).with_for_update().first()

            # Update vote and counts atomically
            if existing_vote:
                if existing_vote.vote_type == vote_type:
                    # Remove vote if clicking same button
                    db.session.delete(existing_vote)
                    if vote_type == 'like':
                        comment.likes = max(0, comment.likes - 1)
                    else:
                        comment.dislikes = max(0, comment.dislikes - 1)
                else:
                    # Change vote type
                    existing_vote.vote_type = vote_type
                    if vote_type == 'like':
                        comment.likes += 1
                        comment.dislikes = max(0, comment.dislikes - 1)
                    else:
                        comment.dislikes += 1
                        comment.likes = max(0, comment.likes - 1)
            else:
                # New vote
                new_vote = Vote(
                    user_id=current_user.id,
                    comment_id=comment_id,
                    vote_type=vote_type
                )
                if vote_type == 'like':
                    comment.likes += 1
                else:
                    comment.dislikes += 1
                db.session.add(new_vote)

            # Update comment author's score
            comment.author.score = db.session.query(
                db.func.sum(Comment.likes - Comment.dislikes)
            ).filter(Comment.user_id == comment.author.id).scalar() or 0

            # Return updated data
            result = {
                'success': True,
                'likes': comment.likes,
                'dislikes': comment.dislikes,
                'user_vote': vote_type,
                'user_id': comment.author.id,
                'user_score': comment.author.score,
                'comment_score': comment.likes - comment.dislikes
            }

            return jsonify(result)

    except exc.SQLAlchemyError as e:
        current_app.logger.error(f"Database error in vote: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Database error occurred while processing vote.'
        }), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in vote: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred while processing vote.'
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