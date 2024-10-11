import json
import pandas as pd

# Load the JSON file
file_path = "universities.json"
with open(file_path, "r") as file:
    data = json.load(file)

# Prepare lists to convert the data into a relational structure
university_list = []
program_list = []
course_list = []

# Process the data
for program_type, states in data["DEGREE_AWARDING_INSTITUTIONS"].items():
    for state, institutions in states.items():
        for institution_name, courses in institutions.items():
            university_list.append(
                {
                    "university_name": institution_name,
                    "state": state,
                    "program_type": program_type,
                }
            )
            for course in courses:
                course_list.append(
                    {
                        "university_name": institution_name,
                        "course_name": course["Course Name"],
                        "abbrv": course["Abbrv."],
                        "direct_entry_requirements": course[
                            "Direct Entry Requirements"
                        ],
                        "utme_requirements": course["UTME Requirements"],
                        "subjects": course["Subjects"],
                    }
                )

# Convert lists to DataFrames
university_df = pd.DataFrame(university_list)
course_df = pd.DataFrame(course_list)

# Save the DataFrames to CSV files
universities_csv_path = "csv/universities.csv"
courses_csv_path = "csv/courses.csv"

university_df.to_csv(universities_csv_path, index=False)
course_df.to_csv(courses_csv_path, index=False)

universities_csv_path, courses_csv_path
