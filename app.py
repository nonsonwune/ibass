# Import required libraries
from flask import Flask, request, render_template, jsonify
import pandas as pd
import os
import logging

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


# API route to get courses by state
@app.route("/api/courses_by_state", methods=["GET"])
def get_courses_by_state():
    state = request.args.get("state")
    if "course_name" in courses_df.columns:
        if state and "state" in universities_df.columns:
            # Filter universities by state
            state_universities = universities_df[universities_df["state"] == state][
                "university_name"
            ].tolist()
            # Filter courses by the universities in the selected state
            state_courses = (
                courses_df[courses_df["university_name"].isin(state_universities)][
                    "course_name"
                ]
                .dropna()
                .unique()
                .tolist()
            )
            return jsonify(sorted(state_courses))
        else:
            # Return all unique courses when no state is selected
            all_courses = courses_df["course_name"].dropna().unique().tolist()
            return jsonify(sorted(all_courses))
    else:
        logging.error("Missing course_name column in courses_df")
        return jsonify([])


# Recommendation route - process user input and give recommendations
@app.route("/recommend", methods=["POST"])
def recommend():
    location = request.form.get("location")
    preferred_course = request.form.get("course")

    logging.info(
        f"Recommendation request - Location: {location}, Course: {preferred_course}"
    )

    filtered_universities = universities_df.copy()
    if location:
        filtered_universities = filtered_universities[
            filtered_universities["state"] == location
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

        # Ensure columns are in the DataFrame before selecting
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

        # Create a mapping of university_name to list of courses
        courses_per_uni = (
            courses_df.groupby("university_name")["course_name"]
            .apply(lambda x: x.tolist() if not x.empty else [])
            .to_dict()
        )
        logging.info(
            f"Courses per university created. Sample: {list(courses_per_uni.items())[:5]}"
        )
        logging.debug(f"Full courses_per_uni dictionary: {courses_per_uni}")

        # Map the courses to each university
        result["courses"] = result["University"].map(courses_per_uni)

        recommendations = result.to_dict(orient="records")
    else:
        recommendations = []

    logging.info(f"Number of recommendations: {len(recommendations)}")

    return render_template(
        "recommend.html",
        recommendations=recommendations,
        location=location,
        course=preferred_course,
    )


# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
