# app/__init__.py
from flask import Flask, render_template
from .extensions import db, login_manager, mail, migrate, csrf
from .config import Config
import logging
from logging.handlers import RotatingFileHandler
import os
from sqlalchemy import event
from .models.interaction import Comment
from .models.user import User
from sqlalchemy.orm import Session
from sqlalchemy import func, select

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

def register_blueprints(app):
    from .views import main_bp, auth_bp, admin_bp, university_bp, api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(university_bp)
    app.register_blueprint(api_bp)

def setup_logging(app):
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/university_finder.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('University Finder startup')

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

    register_extensions(app)
    register_blueprints(app)
    setup_logging(app)
    register_error_handlers(app)
    register_shell_context(app)
    
    # Ensure the user score listeners are set up
    setup_user_score_listeners()

    return app