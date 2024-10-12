import sqlite3
import pandas as pd


def transfer_data():
    # Connect to the SQLite database
    conn = sqlite3.connect("university_courses.db")
    cursor = conn.cursor()

    # Read CSV files
    universities_df = pd.read_csv("universities.csv")
    courses_df = pd.read_csv("courses.csv")

    # Insert universities data
    universities_df.to_sql("universities", conn, if_exists="append", index=False)

    # Insert courses data
    courses_df.to_sql("courses", conn, if_exists="append", index=False)

    # Commit changes and close connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    transfer_data()
