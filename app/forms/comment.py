# app/forms/comment.py
from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length

class InstitutionCommentForm(FlaskForm):
    comment = TextAreaField('Comment', validators=[
        DataRequired(),
        Length(min=1, max=200)
    ]) 