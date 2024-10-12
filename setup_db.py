import sqlite3


def create_database():
    conn = sqlite3.connect("university_courses.db")
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS universities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_name TEXT NOT NULL,
        state TEXT NOT NULL,
        program_type TEXT NOT NULL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        university_name TEXT NOT NULL,
        abbrv TEXT,
        direct_entry_requirements TEXT,
        utme_requirements TEXT,
        subjects TEXT,
        FOREIGN KEY (university_name) REFERENCES universities(university_name)
    )
    """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
