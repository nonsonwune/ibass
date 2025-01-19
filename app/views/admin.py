# app/views/admin.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from ..models.user import User
from ..models.interaction import Comment, Vote
from ..models.feedback import Feedback
from ..models.university import University, Course, State, ProgrammeType
from ..models.requirement import CourseRequirement
from ..forms.admin import DeleteUserForm, DeleteCommentForm, DeleteFeedbackForm, UniversityForm, CourseForm
from ..utils.decorators import admin_required
from ..extensions import db
from sqlalchemy.orm import joinedload
from flask import current_app
from ..models.interaction import Bookmark

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
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
            # Begin transaction
            with db.session.begin_nested():
                # Delete related data first
                Comment.query.filter_by(user_id=user_id).delete()
                Vote.query.filter_by(user_id=user_id).delete()
                Bookmark.query.filter_by(user_id=user_id).delete()
                
                # Finally delete the user
                db.session.delete(user)
            
            # Commit the transaction
            db.session.commit()
            current_app.logger.info(f'Successfully deleted user {user_id} and all related data')
            flash('User and all related data deleted successfully.', 'success')
            
        except SQLAlchemyError as e:
            db.session.rollback()
            error_msg = str(e)
            current_app.logger.error(f'Error deleting user {user_id}: {error_msg}', exc_info=True)
            flash(f'An error occurred while deleting the user: {error_msg}', 'danger')
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            current_app.logger.error(f'Unexpected error deleting user {user_id}: {error_msg}', exc_info=True)
            flash('An unexpected error occurred while deleting the user.', 'danger')
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
@bp.route('/universities')
@login_required
@admin_required
def universities():
    universities = University.query.options(
        db.joinedload(University.state_info),
        db.joinedload(University.programme_type_info)
    ).all()
    return render_template('admin_universities.html', universities=universities)

@bp.route('/university/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_university():
    form = UniversityForm()
    
    # Populate select fields with choices
    states = State.query.order_by(State.name).all()
    programme_types = ProgrammeType.query.order_by(ProgrammeType.name).all()
    form.state.choices = [(state.name, state.name) for state in states]
    form.program_type.choices = [(pt.name, pt.name) for pt in programme_types]
    
    if form.validate_on_submit():
        state = State.query.filter_by(name=form.state.data).first()
        programme_type = ProgrammeType.query.filter_by(name=form.program_type.data).first()
        
        university = University(
            university_name=form.university_name.data,
            state_info=state,
            programme_type_info=programme_type,
            website=form.website.data,
            established=form.established.data,
            abbrv=form.abbrv.data
        )
        try:
            db.session.add(university)
            db.session.commit()
            flash('University added successfully.', 'success')
            return redirect(url_for('admin.universities'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error adding university: {str(e)}', 'danger')
    return render_template('admin_edit_university.html', form=form)

@bp.route('/university/edit/<int:university_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_university(university_id):
    university = University.query.options(
        db.joinedload(University.state_info),
        db.joinedload(University.programme_type_info)
    ).get_or_404(university_id)
    
    form = UniversityForm(obj=university)
    
    # Populate select fields with choices
    states = State.query.order_by(State.name).all()
    programme_types = ProgrammeType.query.order_by(ProgrammeType.name).all()
    form.state.choices = [(state.name, state.name) for state in states]
    form.program_type.choices = [(pt.name, pt.name) for pt in programme_types]
    
    # Manually set the form data for state and program type
    if not form.is_submitted():
        form.state.data = university.state_info.name if university.state_info else ''
        form.program_type.data = university.programme_type_info.name if university.programme_type_info else ''
        form.website.data = university.website
        form.established.data = university.established
        form.abbrv.data = university.abbrv
    
    if form.validate_on_submit():
        university.university_name = form.university_name.data
        university.state_info = State.query.filter_by(name=form.state.data).first()
        university.programme_type_info = ProgrammeType.query.filter_by(name=form.program_type.data).first()
        university.website = form.website.data
        university.established = form.established.data
        university.abbrv = form.abbrv.data
        try:
            db.session.commit()
            flash('University updated successfully.', 'success')
            return redirect(url_for('admin.universities'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating university: {str(e)}', 'danger')
    return render_template('admin_edit_university.html', form=form, university=university)

@bp.route('/university/delete/<int:university_id>', methods=['POST'])
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
    return redirect(url_for('admin.universities'))

@bp.route('/university/toggle_featured/<int:university_id>', methods=['POST'])
@login_required
@admin_required
def toggle_featured(university_id):
    try:
        university = University.query.get_or_404(university_id)
        
        # If trying to feature a university
        if not university.is_featured:
            # Count current featured universities
            featured_count = University.query.filter_by(is_featured=True).count()
            if featured_count >= 6:
                return jsonify({
                    'success': False,
                    'error': 'Maximum limit of 6 featured institutions reached'
                }), 400
        
        university.is_featured = not university.is_featured
        db.session.commit()
        
        # Return current featured count along with success
        featured_count = University.query.filter_by(is_featured=True).count()
        return jsonify({
            'success': True,
            'is_featured': university.is_featured,
            'featured_count': featured_count
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error toggling featured status for university {university_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to update featured status'
        }), 500

# Course Management Routes
@bp.route('/courses')
@login_required
@admin_required
def courses():
    page = request.args.get('page', 1, type=int)
    courses = (Course.query
              .options(
                  joinedload(Course.requirements)
                  .joinedload(CourseRequirement.university)
              )
              .order_by(Course.course_name)
              .paginate(page=page, per_page=50, error_out=False))
    return render_template('admin_courses.html', courses=courses)

@bp.route('/course/add', methods=['GET', 'POST'])
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
            return redirect(url_for('admin.courses'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error adding course: {str(e)}', 'danger')
    return render_template('admin_edit_course.html', form=form)

@bp.route('/course/edit/<int:course_id>', methods=['GET', 'POST'])
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
            return redirect(url_for('admin.courses'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating course: {str(e)}', 'danger')
    return render_template('admin_edit_course.html', form=form, course=course)

@bp.route('/course/delete/<int:course_id>', methods=['POST'])
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
    return redirect(url_for('admin.courses'))