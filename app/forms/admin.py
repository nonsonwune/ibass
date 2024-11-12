# app/forms/admin.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, Optional

class CourseForm(FlaskForm):
    course_name = StringField('Course Name', validators=[DataRequired(), Length(max=256)])
    code = StringField('Course Code', validators=[Optional(), Length(max=50)])
    university_name = SelectField('University', validators=[Optional()])
    direct_entry_requirements = TextAreaField('Direct Entry Requirements', validators=[Optional()])
    utme_requirements = TextAreaField('UTME Requirements', validators=[Optional()])
    subjects = TextAreaField('Required Subjects', validators=[Optional()])

class UniversityForm(FlaskForm):
    university_name = StringField('University Name', validators=[DataRequired(), Length(max=256)])
    state = StringField('State', validators=[DataRequired(), Length(max=50)])
    program_type = StringField('Program Type', validators=[DataRequired(), Length(max=50)])
    website = StringField('Website', validators=[Optional(), Length(max=255)])
    established = IntegerField('Year Established', validators=[Optional()])
    abbrv = StringField('Abbreviation', validators=[Optional(), Length(max=255)])

class DeleteUserForm(FlaskForm):
    pass

class DeleteCommentForm(FlaskForm):
    pass

class DeleteFeedbackForm(FlaskForm):
    pass