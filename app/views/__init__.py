# app/views/__init__.py
from .main import bp as main_bp
from .auth import bp as auth_bp
from .admin import bp as admin_bp
from .university import bp as university_bp
from .api import bp as api_bp

__all__ = ['main_bp', 'auth_bp', 'admin_bp', 'university_bp', 'api_bp']