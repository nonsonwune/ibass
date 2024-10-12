# app.py

# Import required libraries
from flask import Flask, request, render_template, jsonify
import pandas as pd
import os
import logging
import math

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load CSV data
if os.path.exists("universities.csv") and os.path.exists("courses.csv"):
    try:
        universities_df = pd.read_csv("universities.csv")
        courses_df = pd.read_csv("courses.csv")
        logging.info("CSV files loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading CSV files: {e}")
        universities_df = pd.DataFrame()
        courses_df = pd.DataFrame()
else:
    logging.warning("CSV files not found.")
    universities_df = pd.DataFrame()
    courses_df = pd.DataFrame()

logging.info(f"Universities DataFrame columns: {universities_df.columns.tolist()}")
logging.info(f"Courses DataFrame columns: {courses_df.columns.tolist()}")


# Home route - form for user input
@app.route("/")
def home():
    return render_template("home.html")


# API route to get locations
@app.route("/api/locations", methods=["GET"])
def get_locations():
    if "state" in universities_df.columns:
        locations = sorted(universities_df["state"].dropna().unique().tolist())
        return jsonify(locations)
    else:
        logging.error("State column not found in universities_df.")
        return jsonify([])


# API route to get universities
@app.route("/api/universities", methods=["GET"])
def get_universities():
    state = request.args.get("state")
    if "university_name" in universities_df.columns:
        if state:
            universities = (
                universities_df[universities_df["state"] == state]["university_name"]
                .dropna()
                .unique()
                .tolist()
            )
        else:
            universities = universities_df["university_name"].dropna().unique().tolist()
        return jsonify(sorted(universities))
    else:
        logging.error("University_name column not found in universities_df.")
        return jsonify([])


# API route to get courses
@app.route("/api/courses", methods=["GET"])
def get_courses():
    state = request.args.get("state")
    university = request.args.get("university")
    if "course_name" in courses_df.columns:
        filtered_courses = courses_df
        if state:
            state_universities = universities_df[universities_df["state"] == state][
                "university_name"
            ].tolist()
            filtered_courses = filtered_courses[
                filtered_courses["university_name"].isin(state_universities)
            ]
        if university:
            filtered_courses = filtered_courses[
                filtered_courses["university_name"] == university
            ]
        courses = filtered_courses["course_name"].dropna().unique().tolist()
        return jsonify(sorted(courses))
    else:
        logging.error("Missing course_name column in courses_df")
        return jsonify([])


# Recommendation route - process user input and give recommendations
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

    filtered_universities = universities_df.copy()
    if location:
        filtered_universities = filtered_universities[
            filtered_universities["state"] == location
        ]
    if preferred_university:
        filtered_universities = filtered_universities[
            filtered_universities["university_name"] == preferred_university
        ]

    logging.info(f"Filtered universities: {filtered_universities.shape[0]}")

    if preferred_course:
        course_universities = courses_df[courses_df["course_name"] == preferred_course][
            "university_name"
        ].tolist()
        filtered_universities = filtered_universities[
            filtered_universities["university_name"].isin(course_universities)
        ]

        course_info = courses_df[courses_df["course_name"] == preferred_course]
        result = pd.merge(
            filtered_universities, course_info, on="university_name", how="inner"
        )

        display_columns = [
            "university_name",
            "state",
            "program_type",
            "course_name",
            "utme_requirements",
            "subjects",
            "direct_entry_requirements",
            "abbrv",
        ]

        rename_dict = {
            "university_name": "University",
            "state": "State",
            "program_type": "Program Type",
            "course_name": "Course",
            "utme_requirements": "UTME Requirements",
            "subjects": "UTME Subjects",
            "direct_entry_requirements": "Direct Entry Requirements",
            "abbrv": "Abbreviation",
        }

        existing_columns = [col for col in display_columns if col in result.columns]
        result = result[existing_columns]
        result.rename(columns=rename_dict, inplace=True)
    else:
        result = filtered_universities[["university_name", "state", "program_type"]]
        result.rename(
            columns={
                "university_name": "University",
                "state": "State",
                "program_type": "Program Type",
            },
            inplace=True,
        )

    if not result.empty:
        result = result.reset_index(drop=True)
        result["id"] = result.index

        # Refactored: Ensure all courses are lists and handle NaN values
        courses_per_uni = (
            courses_df.groupby("university_name")["course_name"]
            .apply(lambda x: x.dropna().tolist() if isinstance(x, pd.Series) else [])
            .to_dict()
        )
        logging.info(
            f"Courses per university created. Sample: {list(courses_per_uni.items())[:5]}"
        )

        # Replace any non-list entries with empty lists to prevent TypeError
        for uni in result["University"]:
            if uni in courses_per_uni:
                if not isinstance(courses_per_uni[uni], list):
                    courses_per_uni[uni] = []
            else:
                courses_per_uni[uni] = []

        result["courses"] = result["University"].map(courses_per_uni)

        recommendations = result.to_dict(orient="records")
    else:
        recommendations = []

    logging.info(f"Number of recommendations: {len(recommendations)}")

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
    if not query:
        return jsonify({"universities": [], "courses": []})

    try:
        universities = (
            universities_df[
                universities_df["university_name"].str.lower().str.contains(query)
            ]["university_name"]
            .unique()
            .tolist()
        )

        course_search_criteria = [
            courses_df["course_name"].str.lower().str.contains(query),
            courses_df["abbrv"].str.lower().str.contains(query),
        ]

        # Combine search criteria using bitwise OR
        combined_criteria = course_search_criteria[0]
        for criteria in course_search_criteria[1:]:
            combined_criteria = combined_criteria | criteria

        courses = (
            courses_df[combined_criteria]["course_name"].dropna().unique().tolist()
        )

        logging.info(
            f"Search query '{query}' returned {len(universities)} universities and {len(courses)} courses."
        )
        return jsonify({"universities": universities, "courses": courses})
    except Exception as e:
        logging.error(f"Error in search function: {str(e)}")
        return jsonify({"error": "An error occurred while processing your search"}), 500


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


# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
