# app.py
import sys
import os
import logging
from datetime import datetime

from flask import (
    Flask,
    request,
    render_template,
    jsonify,
    redirect,
    url_for,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_migrate import Migrate
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    TextAreaField,
    SubmitField,
)
from flask_mail import Mail
from email_verification import (
    generate_verification_token,
    confirm_verification_token,
    send_verification_email,
)

from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app with instance folder
app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "SQLALCHEMY_DATABASE_URI",
    "sqlite:///" + os.path.join(app.instance_path, "university_courses.db"),
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure CSRF protection to accept tokens from headers
app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken"]

# Determine the environment
environment = os.getenv("FLASK_ENV", "production")

if environment == "development":
    app.debug = True
    app.config["DEBUG"] = True
else:
    app.debug = False
    app.config["DEBUG"] = False

# Ensure instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Initialize Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"
csrf = CSRFProtect(app)

# Configure logging
if environment == "development":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s:%(message)s",
        handlers=[logging.StreamHandler()],
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(message)s",
        handlers=[
            logging.StreamHandler(),
            # Example: FileHandler for production logs
            # logging.FileHandler("logs/production.log"),
        ],
    )

# Configure Mail Server
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 465))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "False") == "True"
app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "True") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

# Initialize Flask-Mail
mail = Mail(app)


# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, default=0, nullable=False, index=True)
    comments = db.relationship(
        "Comment", backref="author", lazy=True, cascade="all, delete-orphan"
    )
    votes = db.relationship(
        "Vote", backref="voter", lazy=True, cascade="all, delete-orphan"
    )
    feedback = db.relationship(
        "Feedback", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    bookmarks = db.relationship(
        "Bookmark", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def calculate_score(self):
        return sum(comment.score for comment in self.comments)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    votes = db.relationship(
        "Vote",
        backref="comment",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def score(self):
        return self.likes - self.dislikes


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", name="fk_vote_user_id_user"),
        nullable=False,
    )
    comment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "comment.id", ondelete="CASCADE", name="fk_vote_comment_id_comment"
        ),
        nullable=False,
    )
    vote_type = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "comment_id", name="user_comment_uc"),
    )


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_submitted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", name="fk_feedback_user_id_user"),
        nullable=True,
    )


class University(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(256), unique=True, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    program_type = db.Column(db.String(50), nullable=False)
    courses = db.relationship(
        "Course", backref="university", lazy=True, cascade="all, delete-orphan"
    )
    bookmarks = db.relationship(
        "Bookmark", backref="university", lazy=True, cascade="all, delete-orphan"
    )


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(256), nullable=False)
    university_name = db.Column(
        db.String(256),
        db.ForeignKey("university.university_name"),
        nullable=False,
    )
    abbrv = db.Column(db.Text)
    direct_entry_requirements = db.Column(db.Text)
    utme_requirements = db.Column(db.Text)
    subjects = db.Column(db.Text)
    bookmarks = db.relationship(
        "Bookmark", backref="course", lazy=True, cascade="all, delete-orphan"
    )


# Database Models
class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    university_id = db.Column(
        db.Integer, db.ForeignKey("university.id", ondelete="CASCADE"), nullable=False
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey("course.id", ondelete="CASCADE"), nullable=True
    )
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# Form Classes
class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    subject = StringField("Subject", validators=[DataRequired()])
    message = TextAreaField("Message", validators=[DataRequired()])
    submit = SubmitField("Send Message")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Sign Up")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm New Password", validators=[DataRequired(), EqualTo("new_password")]
    )
    submit = SubmitField("Change Password")


class ResendVerificationForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Resend Verification Email")


class DeleteUserForm(FlaskForm):
    submit = SubmitField("Delete")


class DeleteCommentForm(FlaskForm):
    submit = SubmitField("Delete")


class DeleteFeedbackForm(FlaskForm):
    submit = SubmitField("Delete")


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Helper Function to Get User Votes
def get_user_votes(user):
    votes = {}
    for vote in user.votes:
        votes[vote.comment_id] = vote.vote_type
    return votes


# Custom Unauthorized Handler
@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.headers.get("Accept") and "application/json" in request.headers.get(
        "Accept"
    ):
        return jsonify({"error": "You must be logged in to perform this action."}), 401
    else:
        return redirect(url_for("login", next=request.url))


# Event Listeners to Update User Score
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


# Attach the event listener
event.listen(Comment, "after_insert", update_user_score)
event.listen(Comment, "after_update", update_user_score)
event.listen(Comment, "after_delete", update_user_score)


# Routes
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/api/locations", methods=["GET"])
def get_locations():
    locations = (
        db.session.query(University.state).distinct().order_by(University.state).all()
    )
    return jsonify([location[0] for location in locations])


@app.route("/api/universities", methods=["GET"])
def get_universities():
    state = request.args.get("state")
    if state:
        universities = University.query.filter_by(state=state).all()
    else:
        universities = University.query.all()
    return jsonify(
        [
            {
                "university_name": uni.university_name,
                "state": uni.state,
                "program_type": uni.program_type,
            }
            for uni in universities
        ]
    )


@app.route("/api/courses", methods=["GET"])
def get_courses():
    state = request.args.get("state")
    university = request.args.get("university")
    query = db.session.query(Course).join(University)
    if state:
        query = query.filter(University.state == state)
    if university:
        query = query.filter(University.university_name == university)
    courses = query.order_by(Course.course_name).all()
    return jsonify(
        [
            {
                "id": course.id,
                "course_name": course.course_name,
                "university_name": course.university_name,
                "abbrv": course.abbrv,
                "direct_entry_requirements": course.direct_entry_requirements,
                "utme_requirements": course.utme_requirements,
                "subjects": course.subjects,
            }
            for course in courses
        ]
    )


@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    if request.method == "POST":
        location = request.form.get("location")
        preferred_university = request.form.get("university")
        preferred_course = request.form.get("course")
    else:  # GET request
        location = request.args.get("location")
        preferred_university = request.args.get("university")
        preferred_course = request.args.get("course")

    query = db.session.query(University).outerjoin(Course)
    if location:
        query = query.filter(University.state == location)
    if preferred_university:
        query = query.filter(University.university_name == preferred_university)
    if preferred_course:
        query = query.filter(Course.course_name == preferred_course)

    results = query.order_by(University.university_name, Course.course_name).all()

    recommendations = []
    for uni in results:
        uni_data = {
            "id": uni.id,
            "university_name": uni.university_name,
            "state": uni.state,
            "program_type": uni.program_type,
            "courses": [
                {
                    "id": course.id,
                    "course_name": course.course_name,
                    "utme_requirements": course.utme_requirements,
                    "subjects": course.subjects,
                    "direct_entry_requirements": course.direct_entry_requirements,
                    "abbrv": course.abbrv,
                }
                for course in uni.courses
            ],
        }
        recommendations.append(uni_data)

    # Get user's bookmarks if authenticated
    user_bookmarks = set()
    if current_user.is_authenticated:
        user_bookmarks = set(
            bookmark.university_id for bookmark in current_user.bookmarks
        )

    return render_template(
        "recommend.html",
        recommendations=recommendations,
        location=location,
        university=preferred_university,
        course=preferred_course,
        user_bookmarks=user_bookmarks,  # Add this line
    )


@app.route("/course/<int:course_id>")
def get_course(course_id):
    course = Course.query.get_or_404(course_id)
    return jsonify(
        {
            "id": course.id,
            "course_name": course.course_name,
            "university_name": course.university_name,
            "utme_requirements": course.utme_requirements,
            "subjects": course.subjects,
            "direct_entry_requirements": course.direct_entry_requirements,
            "abbrv": course.abbrv,
        }
    )


@app.route("/api/search", methods=["GET"])
def search():
    query_text = request.args.get("q", "").lower()
    state = request.args.get("state")
    program_type = request.args.get("program_type")

    try:
        universities_query = University.query.filter(
            University.university_name.ilike(f"%{query_text}%")
        )
        if state:
            universities_query = universities_query.filter(
                University.state.ilike(f"%{state}%")
            )
        if program_type:
            universities_query = universities_query.filter(
                University.program_type.ilike(f"%{program_type}%")
            )
        universities = universities_query.all()

        courses_query = Course.query.filter(
            (Course.course_name.ilike(f"%{query_text}%"))
            | (Course.abbrv.ilike(f"%{query_text}%"))
        )
        courses = courses_query.all()

        return {
            "universities": [
                {
                    "university_name": uni.university_name,
                    "state": uni.state,
                    "program_type": uni.program_type,
                }
                for uni in universities
            ],
            "courses": [
                {
                    "id": course.id,
                    "course_name": course.course_name,
                    "university_name": course.university_name,
                    "abbrv": course.abbrv,
                    "direct_entry_requirements": course.direct_entry_requirements,
                    "utme_requirements": course.utme_requirements,
                    "subjects": course.subjects,
                }
                for course in courses
            ],
        }
    except Exception as e:
        app.logger.error(f"Error in search: {str(e)}")
        return {
            "error": "An error occurred while processing your search. Please try again."
        }


@app.route("/search", methods=["GET"])
def search_results():
    query_text = request.args.get("q", "")
    try:
        search_results = search()
        return render_template(
            "search_results.html",
            query=query_text,
            universities=search_results.get("universities", []),
            courses=search_results.get("courses", []),
        )
    except Exception as e:
        app.logger.error(f"Error in search_results: {str(e)}")
        return render_template(
            "search_results.html",
            query=query_text,
            universities=[],
            courses=[],
            error="An error occurred while processing your search. Please try again.",
        )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        confirm_password = form.confirm_password.data

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.", "danger")
            return redirect(url_for("signup"))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("Email already registered.", "danger")
            return redirect(url_for("signup"))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Generate token and send verification email
        token = generate_verification_token(new_user.email)
        send_verification_email(new_user.email, token)

        flash(
            "Account created successfully. A verification email has been sent to your email address.",
            "success",
        )
        return redirect(url_for("login"))

    return render_template("signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember_me.data

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if not user.is_verified:
                flash("Please verify your email address before logging in.", "warning")
                return redirect(url_for("login"))
            login_user(user, remember=remember)
            flash("Logged in successfully.", "success")
            if user.is_admin:
                return redirect(url_for("admin"))
            else:
                next_page = request.args.get("next")
                return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash(
                "Login unsuccessful. Please check username and password.",
                "danger",
            )
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/profile/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    bookmarks = Bookmark.query.filter_by(user_id=user.id).all()
    return render_template("profile.html", user=user, bookmarks=bookmarks)


@app.route("/vote/<int:comment_id>/<action>", methods=["POST"])
@login_required
def vote_route(comment_id, action):
    if action not in ["like", "dislike"]:
        return jsonify({"error": "Invalid action."}), 400

    try:
        comment = Comment.query.get_or_404(comment_id)
        vote = Vote.query.filter_by(
            user_id=current_user.id, comment_id=comment_id
        ).first()

        if vote:
            if vote.vote_type == action:
                # User is unvoting
                db.session.delete(vote)
                if action == "like":
                    comment.likes -= 1
                else:
                    comment.dislikes -= 1
            else:
                # User is switching vote
                vote.vote_type = action
                if action == "like":
                    comment.likes += 1
                    comment.dislikes -= 1
                else:
                    comment.likes -= 1
                    comment.dislikes += 1
        else:
            # User is voting for the first time
            new_vote = Vote(
                user_id=current_user.id, comment_id=comment_id, vote_type=action
            )
            db.session.add(new_vote)
            if action == "like":
                comment.likes += 1
            else:
                comment.dislikes += 1

        db.session.commit()

        # Update user score
        comment.author.score = comment.author.calculate_score()
        db.session.commit()

        # Get updated user votes
        user_votes = get_user_votes(current_user)

        return jsonify(
            {
                "success": True,
                "likes": comment.likes,
                "dislikes": comment.dislikes,
                "score": comment.score,
                "user_votes": user_votes,
            }
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Error processing vote: {str(e)}")
        return jsonify({"error": "An error occurred while processing your vote."}), 500


@app.route("/api/user_votes", methods=["GET"])
@login_required
def get_user_votes_route():
    app.logger.info(f"Accessing /api/user_votes")
    app.logger.info(f"User authenticated: {current_user.is_authenticated}")
    app.logger.info(
        f"User ID: {current_user.id if current_user.is_authenticated else 'N/A'}"
    )
    try:
        votes = Vote.query.filter_by(user_id=current_user.id).all()
        user_votes = {vote.comment_id: vote.vote_type for vote in votes}
        app.logger.info(f"User votes fetched: {user_votes}")
        return jsonify(user_votes), 200
    except SQLAlchemyError as e:
        app.logger.error(f"Error fetching user votes: {str(e)}")
        return jsonify({"error": "An error occurred while fetching user votes."}), 500


@app.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for("home"))

    user = db.session.get(User, user_id)

    if user.is_admin:
        flash("Cannot delete an admin user.", "danger")
        return redirect(url_for("admin"))

    form = DeleteUserForm()
    if form.validate_on_submit():
        try:
            # Delete related comments, votes, and feedback
            Comment.query.filter_by(user_id=user.id).delete()
            Vote.query.filter_by(user_id=user.id).delete()
            Feedback.query.filter_by(user_id=user.id).delete()

            db.session.delete(user)
            db.session.commit()
            flash("User deleted successfully.", "success")
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.error(f"Error deleting user: {str(e)}")
            flash(
                "An error occurred while deleting the user. Please try again.", "danger"
            )
    else:
        flash("Invalid CSRF token.", "danger")

    return redirect(url_for("admin"))


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if current_user.id == comment.user_id or current_user.is_admin:
        try:
            db.session.delete(comment)
            db.session.commit()
            return jsonify(
                {"success": True, "message": "Comment deleted successfully."}
            )
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.error(f"Error deleting comment: {str(e)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "An error occurred while deleting the comment.",
                    }
                ),
                500,
            )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to delete this comment.",
                }
            ),
            403,
        )


@app.route("/delete_feedback/<int:feedback_id>", methods=["POST"])
@login_required
def delete_feedback(feedback_id):
    if not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for("home"))

    feedback = db.session.get(Feedback, feedback_id)
    form = DeleteFeedbackForm()
    if form.validate_on_submit():
        try:
            db.session.delete(feedback)
            db.session.commit()
            flash("Feedback deleted successfully.", "success")
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.error(f"Error deleting feedback: {str(e)}")
            flash(
                "An error occurred while deleting the feedback. Please try again.",
                "danger",
            )
    else:
        flash("Invalid CSRF token.", "danger")
    return redirect(url_for("admin"))


@app.errorhandler(404)
def not_found_error(error):
    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        return jsonify({"error": "Not found."}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        return jsonify({"error": "Internal server error."}), 500
    return render_template("500.html"), 500


@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        subject = form.subject.data
        message = form.message.data

        new_feedback = Feedback(
            name=name, email=email, subject=subject, message=message
        )
        try:
            # If user is logged in, associate feedback with the user
            if current_user.is_authenticated:
                new_feedback.user_id = current_user.id
            db.session.add(new_feedback)
            db.session.commit()
            flash("Thank you for your feedback!", "success")
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.error(f"Error saving feedback: {str(e)}")
            flash(
                "An error occurred while saving your feedback. Please try again.",
                "danger",
            )

        return redirect(url_for("contact"))

    comments = Comment.query.order_by(Comment.date_posted.desc()).all()
    return render_template("contact.html", form=form, comments=comments)


@app.route("/add_comment", methods=["POST"])
@login_required
def add_comment():
    content = request.form.get("comment", "").strip()
    if not content:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("contact"))

    new_comment = Comment(content=content, author=current_user)
    try:
        db.session.add(new_comment)
        db.session.commit()
        flash("Your comment has been added.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Error adding comment: {str(e)}")
        flash(
            "An error occurred while adding your comment. Please try again.", "danger"
        )
    finally:
        db.session.close()

    return redirect(url_for("contact"))


@app.route("/api/institution/<int:uni_id>")
def get_institution_details(uni_id):
    try:
        search_type = request.args.get("search_type", "location")
        selected_course = request.args.get("course", "")

        university = db.session.get(University, uni_id)
        courses = Course.query.filter_by(
            university_name=university.university_name
        ).all()

        if search_type == "course" and selected_course:
            courses = [
                course
                for course in courses
                if course.course_name.lower() == selected_course.lower()
            ]

        response_data = {
            "id": university.id,
            "university_name": university.university_name,
            "state": university.state,
            "program_type": university.program_type,
            "search_type": search_type,
            "selected_course": selected_course,
            "courses": [
                {
                    "id": course.id,
                    "course_name": course.course_name,
                    "utme_requirements": course.utme_requirements or "N/A",
                    "subjects": course.subjects or "N/A",
                    "direct_entry_requirements": course.direct_entry_requirements
                    or "N/A",
                    "abbrv": course.abbrv or "N/A",
                }
                for course in courses
            ],
        }

        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error(f"Error in get_institution_details: {str(e)}", exc_info=True)
        return (
            jsonify({"error": "An error occurred while fetching institution details."}),
            500,
        )


@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        flash("You do not have permission to access the admin page.", "danger")
        return redirect(url_for("home"))

    users = User.query.all()
    comments = Comment.query.order_by(Comment.date_posted.desc()).all()
    feedback_messages = Feedback.query.order_by(Feedback.date_submitted.desc()).all()

    # Instantiate forms for deleting users and comments
    delete_user_forms = {}
    for user in users:
        if not user.is_admin:
            form = DeleteUserForm()
            delete_user_forms[user.id] = form

    delete_comment_forms = {}
    for comment in comments:
        form = DeleteCommentForm()
        delete_comment_forms[comment.id] = form

    # Instantiate forms for deleting feedback
    delete_feedback_forms = {}
    for feedback in feedback_messages:
        form = DeleteFeedbackForm()
        delete_feedback_forms[feedback.id] = form

    return render_template(
        "admin.html",
        users=users,
        comments=comments,
        feedback_messages=feedback_messages,
        delete_user_forms=delete_user_forms,
        delete_comment_forms=delete_comment_forms,
        delete_feedback_forms=delete_feedback_forms,  # Pass the new forms
    )


@app.route("/verify_email/<token>")
def verify_email(token):
    try:
        email = confirm_verification_token(token)
    except Exception:
        flash("The confirmation link is invalid or has expired.", "danger")
        return redirect(url_for("login"))

    user = db.session.get(User, email=email)
    if user.is_verified:
        flash("Account already verified. Please log in.", "success")
    else:
        user.is_verified = True
        db.session.commit()
        flash("Your account has been verified. You can now log in.", "success")
    return redirect(url_for("login"))


@app.route("/resend_verification", methods=["GET", "POST"])
def resend_verification():
    form = ResendVerificationForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user and not user.is_verified:
            token = generate_verification_token(user.email)
            send_verification_email(user.email, token)
            flash(
                "A new verification email has been sent to your email address.",
                "success",
            )
        else:
            flash(
                "Email address is not associated with any account or already verified.",
                "danger",
            )
        return redirect(url_for("login"))
    return render_template("resend_verification.html", form=form)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if check_password_hash(current_user.password, form.current_password.data):
            current_user.password = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash("Your password has been updated!", "success")
            return redirect(url_for("profile", username=current_user.username))
        else:
            flash("Invalid current password.", "danger")
    return render_template("change_password.html", form=form)


@app.route("/bookmark", methods=["POST"])
@login_required
def add_bookmark():
    app.logger.info("Bookmark route accessed")
    data = request.json
    app.logger.info(f"Received data: {data}")
    university_id = data.get("university_id")

    # Validate university_id
    university = University.query.get(university_id)
    if not university:
        app.logger.warning(f"Invalid university ID: {university_id}")
        return jsonify({"success": False, "message": "Invalid university."}), 400

    # Check if the bookmark already exists
    existing_bookmark = Bookmark.query.filter_by(
        user_id=current_user.id, university_id=university_id
    ).first()
    if existing_bookmark:
        app.logger.info(
            f"Bookmark already exists for user {current_user.id} and university {university_id}"
        )
        return jsonify({"success": True, "message": "Already bookmarked"}), 200

    # Add the bookmark
    try:
        bookmark = Bookmark(user_id=current_user.id, university_id=university_id)
        db.session.add(bookmark)
        db.session.commit()
        app.logger.info(
            f"Bookmark added for user {current_user.id} and university {university_id}"
        )
        return (
            jsonify(
                {"success": True, "message": "Institution bookmarked successfully."}
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding bookmark: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while bookmarking. Please try again.",
                }
            ),
            500,
        )


@app.route("/remove_bookmark/<int:bookmark_id>", methods=["POST"])
@login_required
def remove_bookmark(bookmark_id):
    bookmark = db.session.get(Bookmark, bookmark_id)
    if bookmark.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized action"}), 403
    try:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({"success": True, "message": "Bookmark removed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# Database initialization function using SQLAlchemy
def init_db():
    try:

        # Add missing columns
        with app.app_context():
            # Reflect the database
            db.reflect()
            # Check if 'is_verified' column exists
            if not hasattr(User, "is_verified"):
                with db.engine.connect() as conn:
                    conn.execute(
                        "ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"
                    )

        # Update user emails if necessary
        users = User.query.all()
        for user in users:
            if not user.email or user.email.endswith("@example.com"):
                user.email = f"{user.username}@example.com"

        db.session.commit()

        # Create admin user if not exists
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin = User(
                username="admin",
                email="admin@example.com",
                password=generate_password_hash("adminpassword"),
                is_admin=True,
                is_verified=True,  # Set is_verified to True
            )
            db.session.add(admin)
            db.session.commit()
            logging.info("Admin user created and verified.")
        else:
            logging.info("Admin user already exists.")

        logging.info("Database initialized successfully.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        db.session.close()


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5001)
elif "gunicorn" in sys.modules:
    # If using Gunicorn, you can choose to initialize the DB or assume it's already initialized
    with app.app_context():
        init_db()
else:
    # Do not initialize the DB when running Flask CLI commands
    pass
