# app/models/__init__.py
from .user import User
from .university import University, Course, State, ProgrammeType
from .requirement import (
    CourseRequirement, 
    SubjectRequirement,
    InstitutionalVariation,
    InstitutionalRequirement,
    ExtendedSubjectRequirement,
    ExtendedProgramRequirement,
    DegreeAffiliation,
    DistanceLearning,
    DistanceLearningRequirement,
    TeachingRequirement
)
from .interaction import Comment, Vote, Bookmark
from .feedback import Feedback
from .academic import (
    CertificationHierarchy,
    CatchmentArea,
    CatchmentState,
    AlternativeQualification,
    AcademicRequirement,
    SubjectEquivalency
)
from .subject_classification import (
    SubjectCategoryTypes,
    SubjectClassifications,
    ClassifiedSubjects
)

__all__ = [
    'User',
    'University',
    'Course',
    'State',
    'ProgrammeType',
    'Comment',
    'Vote',
    'Bookmark',
    'Feedback',
    'CourseRequirement',
    'SubjectRequirement',
    'InstitutionalVariation',
    'InstitutionalRequirement',
    'ExtendedSubjectRequirement',
    'ExtendedProgramRequirement',
    'DegreeAffiliation',
    'DistanceLearning',
    'DistanceLearningRequirement',
    'TeachingRequirement',
    'CertificationHierarchy',
    'CatchmentArea',
    'CatchmentState',
    'AlternativeQualification',
    'AcademicRequirement',
    'SubjectEquivalency',
    'SubjectCategoryTypes',
    'SubjectClassifications',
    'ClassifiedSubjects'
]