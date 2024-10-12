import sqlite3
import pandas as pd
from setup_db import create_database


def migrate_to_sqlite():
    # Create new SQLite database
    conn = sqlite3.connect("university_courses.db")
    cursor = conn.cursor()

    # Create tables (reuse the create_database function)
    create_database()

    # Read existing CSV files
    universities_df = pd.read_csv("universities.csv")
    courses_df = pd.read_csv("courses.csv")

    # Insert data into SQLite tables
    universities_df.to_sql("universities", conn, if_exists="append", index=False)
    courses_df.to_sql("courses", conn, if_exists="append", index=False)

    # Create indexes
    cursor.execute("CREATE INDEX idx_university_name ON universities(university_name)")
    cursor.execute("CREATE INDEX idx_course_name ON courses(course_name)")
    cursor.execute("CREATE INDEX idx_university_state ON universities(state)")

    conn.commit()
    conn.close()

    print("Migration completed successfully.")


if __name__ == "__main__":
    migrate_to_sqlite()
