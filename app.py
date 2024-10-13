# app.py

from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
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
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here"  # Replace with a secure key
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///university_courses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    comments = db.relationship("Comment", backref="author", lazy=True)
    votes = db.relationship("Vote", backref="voter", lazy=True)

    @property
    def score(self):
        return sum(comment.score for comment in self.comments)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    votes = db.relationship("Vote", backref="comment", lazy=True)

    @property
    def score(self):
        return self.likes - self.dislikes


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=False)
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


class University(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    university_name = db.Column(db.String(100), unique=True, nullable=False)
    state = db.Column(db.String(50), nullable=False)
    program_type = db.Column(db.String(50), nullable=False)
    courses = db.relationship("Course", backref="university", lazy=True)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    university_name = db.Column(
        db.String(100), db.ForeignKey("university.university_name"), nullable=False
    )
    abbrv = db.Column(db.String(20))
    direct_entry_requirements = db.Column(db.String(200))
    utme_requirements = db.Column(db.String(200))
    subjects = db.Column(db.String(200))


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        subject = request.form["subject"]
        message = request.form["message"]

        new_feedback = Feedback(
            name=name, email=email, subject=subject, message=message
        )
        db.session.add(new_feedback)
        db.session.commit()

        flash("Thank you for your feedback!", "success")
        return redirect(url_for("contact"))

    comments = Comment.query.order_by(Comment.date_posted.desc()).all()
    return render_template("contact.html", comments=comments)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists", "danger")
            return redirect(url_for("signup"))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("Email already registered", "danger")
            return redirect(url_for("signup"))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        remember = "remember_me" in request.form

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash("Logged in successfully", "success")
            if user.is_admin:
                return redirect(url_for("admin"))
            else:
                next_page = request.args.get("next")
                return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash("Login unsuccessful. Please check username and password", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for("home"))


@app.route("/add_comment", methods=["POST"])
@login_required
def add_comment():
    content = request.form["comment"]
    if not content.strip():
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("contact"))
    new_comment = Comment(content=content, author=current_user)
    db.session.add(new_comment)
    db.session.commit()
    flash("Your comment has been added", "success")
    return redirect(url_for("contact"))


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user and not current_user.is_admin:
        flash("You do not have permission to delete this comment", "danger")
        return redirect(url_for("contact"))
    db.session.delete(comment)
    db.session.commit()
    flash("Comment has been deleted", "success")
    return redirect(url_for("contact"))


@app.route("/vote", methods=["POST"])
@login_required
def vote():
    comment_id = request.form.get("comment_id")
    vote_type = request.form.get("vote_type")

    comment = Comment.query.get_or_404(comment_id)

    existing_vote = Vote.query.filter_by(
        user_id=current_user.id, comment_id=comment.id
    ).first()

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
            if vote_type == "like":
                comment.likes -= 1
            else:
                comment.dislikes -= 1
            message = "Vote removed"
        else:
            existing_vote.vote_type = vote_type
            existing_vote.timestamp = datetime.utcnow()
            if vote_type == "like":
                comment.likes += 1
                comment.dislikes -= 1
            else:
                comment.likes -= 1
                comment.dislikes += 1
            message = "Vote changed"
    else:
        new_vote = Vote(
            user_id=current_user.id, comment_id=comment.id, vote_type=vote_type
        )
        db.session.add(new_vote)
        if vote_type == "like":
            comment.likes += 1
        else:
            comment.dislikes += 1
        message = "Vote recorded"

    db.session.commit()

    return jsonify({"success": True, "new_score": comment.score, "message": message})


@app.route("/api/user_votes", methods=["GET"])
@login_required
def get_user_votes():
    votes = Vote.query.filter_by(user_id=current_user.id).all()
    user_votes = {vote.comment_id: vote.vote_type for vote in votes}
    return jsonify(user_votes)


@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        flash("You do not have permission to access this page", "danger")
        return redirect(url_for("home"))

    feedback = Feedback.query.order_by(Feedback.date_submitted.desc()).all()
    comments = Comment.query.order_by(Comment.date_posted.desc()).all()
    return render_template("admin.html", feedback=feedback, comments=comments)


@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    old_password = request.form["old_password"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    if not check_password_hash(current_user.password, old_password):
        flash("Old password is incorrect", "danger")
        return redirect(url_for("admin"))

    if new_password != confirm_password:
        flash("New passwords do not match", "danger")
        return redirect(url_for("admin"))

    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    flash("Password changed successfully", "success")
    return redirect(url_for("admin"))


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
        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error in get_institution_details: {str(e)}", exc_info=True)
        return (
            jsonify({"error": "An error occurred while fetching institution details"}),
            500,
        )


@app.route("/profile/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template("profile.html", user=user)


if __name__ == "__main__":
    app.run(debug=True)
