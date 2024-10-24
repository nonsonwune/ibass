# app/forms/__init__.py
from .auth import LoginForm, SignupForm, ChangePasswordForm, ResendVerificationForm
from .admin import DeleteUserForm, DeleteCommentForm, DeleteFeedbackForm
from .feedback import ContactForm

__all__ = [
    'LoginForm',
    'SignupForm',
    'ChangePasswordForm',
    'ResendVerificationForm',
    'DeleteUserForm',
    'DeleteCommentForm',
    'DeleteFeedbackForm',
    'ContactForm'
]