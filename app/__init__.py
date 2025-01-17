# app/__init__.py
from flask import Flask, render_template, request
from .extensions import db, login_manager, mail, migrate, csrf, cache
from .config import Config
import logging
from logging.handlers import RotatingFileHandler
import os
from sqlalchemy import event
from .models.interaction import Comment
from .models.user import User
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from .utils.startup import verify_database_setup  # Add this import

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    cache.init_app(app, config={
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300
    })

    # Add database verification after extensions are initialized
    with app.app_context():
        try:
            verify_database_setup()
            app.logger.info("Database verification successful")
        except Exception as e:
            app.logger.error(f"Database verification failed: {str(e)}")
            # Don't raise the exception - allow the app to start with degraded search functionality
            app.logger.warning("Application starting with degraded search functionality")

def register_blueprints(app):
    from .views import main_bp, auth_bp, admin_bp, university_bp, api_bp
    # Removed search_api_bp to centralize API routes within api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(university_bp)
    app.register_blueprint(api_bp, url_prefix='/api')  # api_bp handles all /api routes

def setup_logging(app):
    import logging
    from logging.handlers import RotatingFileHandler
    import os

    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Configure root logger to only show INFO and above in terminal
    logging.basicConfig(level=getattr(logging, app.config['LOG_LEVEL']))
    root_logger = logging.getLogger()
    
    # Remove existing handlers from root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler for important logs only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Configure formatters
    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    detailed_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Application log handler (file only)
    app_handler = RotatingFileHandler(
        'logs/application.log',
        maxBytes=10240,
        backupCount=10
    )
    app_handler.setFormatter(file_formatter)
    app_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.addHandler(app_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

    # SQL query log handler (file only)
    sql_handler = RotatingFileHandler(
        'logs/sql.log',
        maxBytes=10240,
        backupCount=5
    )
    sql_handler.setFormatter(detailed_formatter)
    sql_handler.setLevel(getattr(logging, app.config['SQLALCHEMY_LOG_LEVEL']))

    # Configure SQLAlchemy logging
    sql_logger = logging.getLogger('sqlalchemy.engine')
    sql_logger.addHandler(sql_handler)
    sql_logger.setLevel(getattr(logging, app.config['SQLALCHEMY_LOG_LEVEL']))
    sql_logger.propagate = False  # Prevent duplicate logs
    
    # Remove duplicate handlers if any
    for handler in sql_logger.handlers[:-1]:
        sql_logger.removeHandler(handler)

    # Query timing log handler (file only)
    timing_handler = RotatingFileHandler(
        'logs/query_timing.log',
        maxBytes=10240,
        backupCount=5
    )
    timing_handler.setFormatter(detailed_formatter)
    timing_handler.setLevel(logging.DEBUG)

    # Configure query timing logging
    timing_logger = logging.getLogger('query_timing')
    timing_logger.addHandler(timing_handler)
    timing_logger.setLevel(logging.DEBUG)
    timing_logger.propagate = False  # Prevent duplicate logs
    
    # Remove duplicate handlers if any
    for handler in timing_logger.handlers[:-1]:
        timing_logger.removeHandler(handler)

    app.logger.info('Logging setup completed')

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User': User}

def setup_user_score_listeners():
    def update_user_score(mapper, connection, target):
        if target.author:
            user_id = target.author.id
            with Session(connection) as session:
                score = (
                    session.execute(
                        select(func.sum(Comment.likes - Comment.dislikes)).where(
                            Comment.user_id == user_id
                        )
                    ).scalar()
                    or 0
                )
                session.execute(
                    User.__table__.update().where(User.id == user_id).values(score=score)
                )
        else:
            logging.warning(f"Comment ID {target.id} has no associated user.")

    event.listen(Comment, "after_insert", update_user_score)
    event.listen(Comment, "after_update", update_user_score)
    event.listen(Comment, "after_delete", update_user_score)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    setup_logging(app)  # Move logging setup before extensions
    register_extensions(app)  # Database verification happens here
    register_blueprints(app)
    register_error_handlers(app)
    register_shell_context(app)
    setup_user_score_listeners()
    
    # Register CLI commands
    from .cli import init_app as init_cli
    init_cli(app)

    @csrf.exempt
    def get_requests():
        return request.method == 'GET'

    return app