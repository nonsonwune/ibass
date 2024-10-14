# app.py

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
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    TextAreaField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, EqualTo
from flask_wtf.csrf import CSRFProtect
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = (
    "your_secure_secret_key"  # Replace with a secure key in production
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///university_courses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
    handlers=[logging.StreamHandler()],
)


# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    comments = db.relationship(
        "Comment", backref="author", lazy=True, cascade="all, delete-orphan"
    )
    votes = db.relationship(
        "Vote", backref="voter", lazy=True, cascade="all, delete-orphan"
    )
    feedback = db.relationship(
        "Feedback", backref="user", lazy=True, cascade="all, delete-orphan"
    )


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
    university_name = db.Column(db.String(100), unique=True, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    program_type = db.Column(db.String(50), nullable=False)
    courses = db.relationship(
        "Course", backref="university", lazy=True, cascade="all, delete-orphan"
    )


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    university_name = db.Column(
        db.String(100),
        db.ForeignKey("university.university_name"),
        nullable=False,
    )
    abbrv = db.Column(db.String(20))
    direct_entry_requirements = db.Column(db.String(200))
    utme_requirements = db.Column(db.String(200))
    subjects = db.Column(db.String(200))


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


class DeleteUserForm(FlaskForm):
    submit = SubmitField("Delete")


class DeleteCommentForm(FlaskForm):
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
    # Check if the request expects JSON (i.e., is an AJAX request)
    if request.headers.get("Accept") and "application/json" in request.headers.get(
        "Accept"
    ):
        return jsonify({"error": "You must be logged in to perform this action."}), 401
    else:
        return redirect(url_for("login", next=request.url))


# Database initialization function using SQLAlchemy
def init_db():
    db.create_all()

    # Assign unique emails to existing users if needed
    users = User.query.all()
    for user in users:
        if not user.email or user.email.endswith("@example.com"):
            user.email = f"{user.username}@example.com"
    db.session.commit()

    # Insert admin user if not exists
    admin_user = User.query.filter_by(username="admin").first()
    if not admin_user:
        admin = User(
            username="admin",
            email="admin@example.com",
            password=generate_password_hash("adminpassword"),
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
        logging.info("Admin user created.")
    else:
        logging.info("Admin user already exists.")


# Initialize the database
with app.app_context():
    init_db()


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

    logging.info(
        f"Recommendation request - Location: {location}, University: {preferred_university}, Course: {preferred_course}"
    )

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

    logging.info(f"Number of recommendations: {len(recommendations)}")
    if recommendations:
        logging.debug(f"Sample recommendation: {recommendations[0]}")
    else:
        logging.debug("No recommendations found.")

    return render_template(
        "recommend.html",
        recommendations=recommendations,
        location=location,
        university=preferred_university,
        course=preferred_course,
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

    return jsonify(
        {
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
    )


@app.route("/search", methods=["GET"])
def search_results():
    query_text = request.args.get("q", "")
    search_results = search()
    if isinstance(search_results, tuple):
        search_results = search_results[0].get_json()
    return render_template(
        "search_results.html",
        query=query_text,
        universities=search_results.get("universities", []),
        courses=search_results.get("courses", []),
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        if request.method == "POST":
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

            flash("Account created successfully.", "success")
            return redirect(url_for("login"))

    return render_template("signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if request.method == "POST":
            username = form.username.data
            password = form.password.data
            remember = form.remember_me.data

            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user, remember=remember)
                flash("Logged in successfully.", "success")
                if user.is_admin:
                    return redirect(url_for("admin"))
                else:
                    next_page = request.args.get("next")
                    return (
                        redirect(next_page) if next_page else redirect(url_for("home"))
                    )
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
    return render_template("profile.html", user=user)


@app.route("/vote/<int:comment_id>/<action>", methods=["POST"])
@login_required
def vote(comment_id, action):
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
                old_vote_type = vote.vote_type
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
                user_id=current_user.id,
                comment_id=comment_id,
                vote_type=action,
            )
            db.session.add(new_vote)
            if action == "like":
                comment.likes += 1
            else:
                comment.dislikes += 1

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
    try:
        votes = Vote.query.filter_by(user_id=current_user.id).all()
        user_votes = {vote.comment_id: vote.vote_type for vote in votes}
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

    user = User.query.get_or_404(user_id)

    if user.is_admin:
        flash("Cannot delete an admin user.", "danger")
        return redirect(url_for("admin"))

    form = DeleteUserForm()
    if form.validate_on_submit():
        try:
            # Log the CSRF token for debugging (remove in production)
            csrf_token = form.csrf_token.data
            app.logger.info(f"CSRF Token Received: {csrf_token}")

            # Delete related comments, votes, and feedback
            Comment.query.filter_by(user_id=user.id).delete()
            Vote.query.filter_by(user_id=user.id).delete()
            Feedback.query.filter_by(user_id=user.id).delete()

            db.session.delete(user)
            db.session.commit()
            flash("User deleted successfully.", "success")
            app.logger.info(f"User with ID {user_id} deleted successfully.")
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
    comment = Comment.query.get_or_404(comment_id)
    if current_user.id == comment.user_id or current_user.is_admin:
        form = DeleteCommentForm()
        if form.validate_on_submit():
            try:
                # Log the CSRF token for debugging (remove in production)
                csrf_token = form.csrf_token.data
                app.logger.info(f"CSRF Token Received: {csrf_token}")

                db.session.delete(comment)
                db.session.commit()
                flash("Comment deleted successfully.", "success")
                app.logger.info(f"Comment with ID {comment_id} deleted successfully.")
            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f"Error deleting comment: {str(e)}")
                flash(
                    "An error occurred while deleting the comment. Please try again.",
                    "danger",
                )
        else:
            flash("Invalid CSRF token.", "danger")
    else:
        flash("You do not have permission to delete this comment.", "danger")
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
            "An error occurred while adding your comment. Please try again.",
            "danger",
        )

    return redirect(url_for("contact"))


@app.route("/api/institution/<int:uni_id>")
def get_institution_details(uni_id):
    try:
        search_type = request.args.get("search_type", "location")
        selected_course = request.args.get("course", "")

        logging.info(f"Fetching details for institution ID: {uni_id}")
        logging.info(f"Search type: {search_type}, Selected course: {selected_course}")

        university = University.query.get_or_404(uni_id)
        courses = Course.query.filter_by(
            university_name=university.university_name
        ).all()

        logging.info(f"Found {len(courses)} courses for {university.university_name}")

        if search_type == "course" and selected_course:
            courses = [
                course
                for course in courses
                if course.course_name.lower() == selected_course.lower()
            ]
            logging.info(
                f"Filtered to {len(courses)} courses matching '{selected_course}'"
            )

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
                    "utme_requirements": course.utme_requirements,
                    "subjects": course.subjects,
                    "direct_entry_requirements": course.direct_entry_requirements,
                    "abbrv": course.abbrv,
                }
                for course in courses
            ],
        }

        logging.info(f"Sending response: {response_data}")
        return jsonify(response_data), 200
    except Exception as e:
        logging.error(f"Error in get_institution_details: {str(e)}", exc_info=True)
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

    # Admin functionalities: list all users, comments, and feedback
    users = User.query.all()
    comments = Comment.query.order_by(Comment.date_posted.desc()).all()
    feedback_messages = Feedback.query.order_by(Feedback.date_submitted.desc()).all()

    # Create DeleteUserForm and DeleteCommentForm for each user and comment
    delete_user_forms = {}
    for user in users:
        if not user.is_admin:
            form = DeleteUserForm()
            delete_user_forms[user.id] = form

    delete_comment_forms = {}
    for comment in comments:
        form = DeleteCommentForm()
        delete_comment_forms[comment.id] = form

    return render_template(
        "admin.html",
        users=users,
        comments=comments,
        feedback_messages=feedback_messages,
        delete_user_forms=delete_user_forms,
        delete_comment_forms=delete_comment_forms,
    )


@app.route("/delete_feedback/<int:feedback_id>", methods=["POST"])
@login_required
def delete_feedback(feedback_id):
    if not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for("home"))

    feedback = Feedback.query.get_or_404(feedback_id)
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
    return redirect(url_for("admin"))


@app.route("/test_csrf", methods=["GET", "POST"])
def test_csrf():
    form = FlaskForm()
    if form.validate_on_submit():
        flash("CSRF token validated successfully.", "success")
        return redirect(url_for("home"))
    return render_template("test_csrf.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)
