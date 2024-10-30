# app/forms/admin.py
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, IntegerField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional

class DeleteUserForm(FlaskForm):
    submit = SubmitField('Delete')

class DeleteCommentForm(FlaskForm):
    submit = SubmitField('Delete')

class DeleteFeedbackForm(FlaskForm):
    submit = SubmitField('Delete')
    
class UniversityForm(FlaskForm):
    university_name = StringField('University Name', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    program_type = StringField('Program Type', validators=[DataRequired()])
    website = StringField('Website', validators=[Optional()])
    established = IntegerField('Established Year', validators=[Optional()])
    abbrv = StringField('Abbreviation', validators=[Optional()])  # Added this line
    submit = SubmitField('Save')

class CourseForm(FlaskForm):
    course_name = StringField('Course Name', validators=[DataRequired()])
    university_name = SelectField('University', validators=[DataRequired()], coerce=str)
    direct_entry_requirements = TextAreaField('Direct Entry Requirements', validators=[Optional()])
    utme_requirements = TextAreaField('UTME Requirements', validators=[Optional()])
    subjects = TextAreaField('Subjects', validators=[Optional()])
    submit = SubmitField('Save')