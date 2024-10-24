from flask_wtf import FlaskForm
from wtforms import SubmitField

class DeleteUserForm(FlaskForm):
    submit = SubmitField('Delete')

class DeleteCommentForm(FlaskForm):
    submit = SubmitField('Delete')

class DeleteFeedbackForm(FlaskForm):
    submit = SubmitField('Delete')