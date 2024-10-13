from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
import sqlite3
import logging
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"  # Replace with a real secret key
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


# Database initialization
def init_db():
    with sqlite3.connect("university_courses.db") as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS universities
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         university_name TEXT NOT NULL,
                         state TEXT NOT NULL,
                         program_type TEXT NOT NULL)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS courses
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         course_name TEXT NOT NULL,
                         university_name TEXT NOT NULL,
                         abbrv TEXT,
                         direct_entry_requirements TEXT,
                         utme_requirements TEXT,
                         subjects TEXT)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS feedback
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         name TEXT NOT NULL,
                         email TEXT NOT NULL,
                         subject TEXT NOT NULL,
                         message TEXT NOT NULL)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         username TEXT UNIQUE NOT NULL,
                         password TEXT NOT NULL)"""
        )


# Initialize database
init_db()


# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user["id"], user["username"])
    return None


# Database connection helper
def get_db_connection():
    conn = sqlite3.connect("university_courses.db")
    conn.row_factory = sqlite3.Row
    return conn


# Home route
@app.route("/")
def home():
    return render_template("home.html")


# API route to get locations
@app.route("/api/locations", methods=["GET"])
def get_locations():
    conn = get_db_connection()
    locations = conn.execute(
        "SELECT DISTINCT state FROM universities ORDER BY state"
    ).fetchall()
    conn.close()
    return jsonify([location["state"] for location in locations])


# API route to get universities
@app.route("/api/universities", methods=["GET"])
def get_universities():
    state = request.args.get("state")
    conn = get_db_connection()
    if state:
        universities = conn.execute(
            "SELECT university_name, state, program_type FROM universities WHERE state = ?",
            (state,),
        ).fetchall()
    else:
        universities = conn.execute(
            "SELECT university_name, state, program_type FROM universities"
        ).fetchall()
    conn.close()
    return jsonify([dict(uni) for uni in universities])


# API route to get courses
@app.route("/api/courses", methods=["GET"])
def get_courses():
    state = request.args.get("state")
    university = request.args.get("university")
    conn = get_db_connection()
    query = """SELECT c.course_name, c.university_name, c.abbrv, c.direct_entry_requirements, c.utme_requirements, c.subjects
               FROM courses c
               JOIN universities u ON c.university_name = u.university_name
               WHERE 1=1"""
    params = []
    if state:
        query += " AND u.state = ?"
        params.append(state)
    if university:
        query += " AND c.university_name = ?"
        params.append(university)
    query += " ORDER BY c.course_name"
    courses = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(course) for course in courses])


# Recommendation route
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

    conn = get_db_connection()
    query = """SELECT u.university_name, u.state, u.program_type, 
                      c.course_name, c.utme_requirements, c.subjects, 
                      c.direct_entry_requirements, c.abbrv
               FROM universities u
               LEFT JOIN courses c ON u.university_name = c.university_name
               WHERE 1=1"""
    params = []

    if location:
        query += " AND u.state = ?"
        params.append(location)
    if preferred_university:
        query += " AND u.university_name = ?"
        params.append(preferred_university)
    if preferred_course:
        query += " AND c.course_name = ?"
        params.append(preferred_course)

    query += " ORDER BY u.university_name, c.course_name"

    results = conn.execute(query, params).fetchall()
    conn.close()

    grouped_recommendations = {}
    for row in results:
        uni_name = row["university_name"]
        if uni_name not in grouped_recommendations:
            grouped_recommendations[uni_name] = {
                "id": len(grouped_recommendations),
                "university_name": uni_name,
                "state": row["state"],
                "program_type": row["program_type"],
                "courses": [],
                "added_courses": set(),
            }

        if (
            row["course_name"]
            and row["course_name"]
            not in grouped_recommendations[uni_name]["added_courses"]
        ):
            grouped_recommendations[uni_name]["courses"].append(
                {
                    "course_name": row["course_name"],
                    "utme_requirements": row["utme_requirements"],
                    "subjects": row["subjects"],
                    "direct_entry_requirements": row["direct_entry_requirements"],
                    "abbrv": row["abbrv"],
                }
            )
            grouped_recommendations[uni_name]["added_courses"].add(row["course_name"])

    # Remove the "added_courses" set before passing to template
    recommendations = [
        {k: v for k, v in uni.items() if k != "added_courses"}
        for uni in grouped_recommendations.values()
    ]

    logging.info(f"Number of recommendations: {len(recommendations)}")
    logging.debug(
        f"Sample recommendation: {recommendations[0] if recommendations else 'No recommendations'}"
    )

    return render_template(
        "recommend.html",
        recommendations=recommendations,
        location=location,
        university=preferred_university,
        course=preferred_course,
    )


# Search API endpoint
@app.route("/api/search", methods=["GET"])
def search():
    query = request.args.get("q", "").lower()
    state = request.args.get("state")
    program_type = request.args.get("program_type")

    conn = get_db_connection()
    uni_query = """SELECT university_name, state, program_type
                   FROM universities
                   WHERE LOWER(university_name) LIKE ?"""
    uni_params = [f"%{query}%"]

    if state:
        uni_query += " AND LOWER(state) = ?"
        uni_params.append(state.lower())
    if program_type:
        uni_query += " AND LOWER(program_type) = ?"
        uni_params.append(program_type.lower())

    universities = conn.execute(uni_query, uni_params).fetchall()

    course_query = """SELECT course_name, university_name, abbrv, direct_entry_requirements, utme_requirements, subjects
                      FROM courses
                      WHERE LOWER(course_name) LIKE ? OR LOWER(abbrv) LIKE ?"""
    course_params = [f"%{query}%", f"%{query}%"]

    courses = conn.execute(course_query, course_params).fetchall()
    conn.close()

    return jsonify(
        {
            "universities": [dict(uni) for uni in universities],
            "courses": [dict(course) for course in courses],
        }
    )


# Search results route
@app.route("/search", methods=["GET"])
def search_results():
    query = request.args.get("q", "")
    search_results = search().get_json()
    return render_template(
        "search_results.html",
        query=query,
        universities=search_results.get("universities", []),
        courses=search_results.get("courses", []),
    )


# About route
@app.route("/about")
def about():
    return render_template("about.html")


# Contact route
@app.route("/contact")
def contact():
    return render_template("contact.html")


# Feedback submission route
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    subject = request.form.get("subject")
    message = request.form.get("message")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO feedback (name, email, subject, message) VALUES (?, ?, ?, ?)",
        (name, email, subject, message),
    )
    conn.commit()
    conn.close()

    flash("Thank you for your feedback!", "success")
    return redirect(url_for("contact"))


# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            user_obj = User(user["id"], user["username"])
            login_user(user_obj)
            return redirect(url_for("admin"))

        flash("Invalid username or password", "error")

    return render_template("login.html")


# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


# Admin route
@app.route("/admin")
@login_required
def admin():
    conn = get_db_connection()
    feedback = conn.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin.html", feedback=feedback)


# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
