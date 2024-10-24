# app/views/admin.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from ..models.user import User
from ..models.interaction import Comment
from ..models.feedback import Feedback
from ..forms.admin import DeleteUserForm, DeleteCommentForm, DeleteFeedbackForm
from ..utils.decorators import admin_required
from ..extensions import db

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