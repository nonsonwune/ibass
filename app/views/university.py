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
    programme_type = request.args.get('programme_type')
    preferred_university = request.args.get('university')
    preferred_course = request.args.get('course')

    query = db.session.query(University).outerjoin(Course)
    if location:
        query = query.filter(University.state == location)
    if programme_type:
        if programme_type in Config.PROGRAMME_GROUPS:
            programme_types = Config.PROGRAMME_GROUPS[programme_type]
            query = query.filter(University.program_type.in_(programme_types))
        elif programme_type == "ALL_INSTITUTION_TYPES":
            pass
        else:
            query = query.filter(University.program_type == programme_type)
    if preferred_university:
        query = query.filter(University.university_name == preferred_university)
    if preferred_course:
        query = query.filter(Course.course_name == preferred_course)

    results = query.order_by(University.university_name, Course.course_name).all()

    recommendations = []
    for uni in results:
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
            } for course in uni.courses],
            "selected_course": preferred_course,
        }
        recommendations.append(uni_data)

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