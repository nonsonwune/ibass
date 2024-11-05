# app/models/__init__.py
from .user import User
from .university import University, Course
from .requirement import CourseRequirement, SubjectRequirement
from .interaction import Comment, Vote, Bookmark
from .feedback import Feedback

# This allows importing all models from app.models
__all__ = [
    'User',
    'University',
    'Course',
    'Comment',
    'Vote',
    'Bookmark',
    'Feedback',
    'CourseRequirement',
    'SubjectRequirement',
]