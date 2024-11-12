# app/views/admin.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from ..models.user import User
from ..models.interaction import Comment
from ..models.feedback import Feedback
from ..models.university import University, Course
from ..models.requirement import CourseRequirement
from ..forms.admin import DeleteUserForm, DeleteCommentForm, DeleteFeedbackForm, UniversityForm, CourseForm
from ..utils.decorators import admin_required
from ..extensions import db
from sqlalchemy.orm import joinedload

bp = Blueprint('admin', __name__)

@bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.all()
    comments = Comment.query.order_by(Comment.date_posted.desc()).all()
    feedback_messages = Feedback.query.order_by(Feedback.date_submitted.desc()).all()
    
    delete_user_forms = {}
    for user in users:
        if not user.is_admin:
            form = DeleteUserForm()
            delete_user_forms[user.id] = form

    delete_comment_forms = {}
    for comment in comments:
        form = DeleteCommentForm()
        delete_comment_forms[comment.id] = form

    delete_feedback_forms = {}
    for feedback in feedback_messages:
        form = DeleteFeedbackForm()
        delete_feedback_forms[feedback.id] = form

    return render_template('admin.html',
        users=users,
        comments=comments,
        feedback_messages=feedback_messages,
        delete_user_forms=delete_user_forms,
        delete_comment_forms=delete_comment_forms,
        delete_feedback_forms=delete_feedback_forms
    )

@bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.home'))

    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete an admin user.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    form = DeleteUserForm()
    if form.validate_on_submit():
        try:
            db.session.delete(user)
            db.session.commit()
            flash('User deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while deleting the user. Please try again.', 'danger')
    else:
        flash('Invalid CSRF token.', 'danger')

    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user.id == comment.user_id or current_user.is_admin:
        form = DeleteCommentForm()
        if form.validate_on_submit():
            try:
                db.session.delete(comment)
                db.session.commit()
                flash('Comment deleted successfully.', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                flash('An error occurred while deleting the comment.', 'danger')
    else:
        flash('You do not have permission to delete this comment.', 'danger')
    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/delete_feedback/<int:feedback_id>', methods=['POST'])
@login_required
@admin_required
def delete_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    form = DeleteFeedbackForm()
    if form.validate_on_submit():
        try:
            db.session.delete(feedback)
            db.session.commit()
            flash('Feedback deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while deleting the feedback.', 'danger')
    return redirect(url_for('admin.admin_dashboard'))


# University Management Routes
@bp.route('/admin/universities')
@login_required
@admin_required
def admin_universities():
    universities = University.query.all()
    return render_template('admin_universities.html', universities=universities)

@bp.route('/admin/university/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_university():
    form = UniversityForm()
    if form.validate_on_submit():
        university = University(
            university_name=form.university_name.data,
            state=form.state.data,
            program_type=form.program_type.data,
            website=form.website.data,
            established=form.established.data
        )
        try:
            db.session.add(university)
            db.session.commit()
            flash('University added successfully.', 'success')
            return redirect(url_for('admin.admin_universities'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error adding university: {str(e)}', 'danger')
    return render_template('admin_edit_university.html', form=form)

@bp.route('/admin/university/edit/<int:university_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_university(university_id):
    university = University.query.get_or_404(university_id)
    form = UniversityForm(obj=university)
    if form.validate_on_submit():
        university.university_name = form.university_name.data
        university.state = form.state.data
        university.program_type = form.program_type.data
        university.website = form.website.data
        university.established = form.established.data
        try:
            db.session.commit()
            flash('University updated successfully.', 'success')
            return redirect(url_for('admin.admin_universities'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating university: {str(e)}', 'danger')
    return render_template('admin_edit_university.html', form=form, university=university)

@bp.route('/admin/university/delete/<int:university_id>', methods=['POST'])
@login_required
@admin_required
def delete_university(university_id):
    university = University.query.get_or_404(university_id)
    try:
        db.session.delete(university)
        db.session.commit()
        flash('University deleted successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error deleting university: {str(e)}', 'danger')
    return redirect(url_for('admin.admin_universities'))

# Course Management Routes
@bp.route('/admin/courses')
@login_required
@admin_required
def admin_courses():
    page = request.args.get('page', 1, type=int)
    courses = (Course.query
              .options(
                  joinedload(Course.requirements)
                  .joinedload(CourseRequirement.university)
              )
              .order_by(Course.course_name)
              .paginate(page=page, per_page=50, error_out=False))
    return render_template('admin_courses.html', courses=courses)

@bp.route('/admin/course/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_course():
    form = CourseForm()
    form.university_name.choices = [(u.university_name, u.university_name) for u in University.query.order_by(University.university_name).all()]
    if form.validate_on_submit():
        course = Course(
            course_name=form.course_name.data,
            university_name=form.university_name.data,
            direct_entry_requirements=form.direct_entry_requirements.data,
            utme_requirements=form.utme_requirements.data,
            subjects=form.subjects.data
        )
        try:
            db.session.add(course)
            db.session.commit()
            flash('Course added successfully.', 'success')
            return redirect(url_for('admin.admin_courses'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error adding course: {str(e)}', 'danger')
    return render_template('admin_edit_course.html', form=form)

@bp.route('/admin/course/edit/<int:course_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    form = CourseForm(obj=course)
    form.university_name.choices = [(u.university_name, u.university_name) for u in University.query.order_by(University.university_name).all()]
    if form.validate_on_submit():
        course.course_name = form.course_name.data
        course.university_name = form.university_name.data
        course.abbrv = form.abbrv.data
        course.direct_entry_requirements = form.direct_entry_requirements.data
        course.utme_requirements = form.utme_requirements.data
        course.subjects = form.subjects.data
        try:
            db.session.commit()
            flash('Course updated successfully.', 'success')
            return redirect(url_for('admin.admin_courses'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating course: {str(e)}', 'danger')
    return render_template('admin_edit_course.html', form=form, course=course)

@bp.route('/admin/course/delete/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    try:
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'danger')
    return redirect(url_for('admin.admin_courses'))