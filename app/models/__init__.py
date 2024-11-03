# app/models/__init__.py
from .user import User
from .university import University, Course
from .interaction import Comment, Vote, Bookmark
from .feedback import Feedback
from .subject import SubjectCategories, Subjects
from .requirement import (
    CourseRequirementTemplates,
    TemplateSubjectRequirements,
    InstitutionRequirements,
    InstitutionSubjectRequirements)

# This allows importing all models from app.models
__all__ = [
    'User',
    'University',
    'Course',
    'Comment',
    'Vote',
    'Bookmark',
    'Feedback',
    'SubjectCategories',
    'Subjects',
    'CourseRequirementTemplates',
    'TemplateSubjectRequirements',
    'InstitutionRequirements',
    'InstitutionSubjectRequirements'
]