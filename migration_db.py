import pandas as pd
from app import db, University, Course, app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_to_sqlite():
    with app.app_context():
        try:
            # Read existing CSV files
            universities_df = pd.read_csv("universities.csv")
            courses_df = pd.read_csv("courses.csv")

            # Insert universities
            for _, row in universities_df.iterrows():
                university = University(
                    university_name=row["university_name"],
                    state=row["state"],
                    program_type=row["program_type"],
                )
                db.session.add(university)

            db.session.commit()
            logger.info("Universities data migrated successfully.")

            # Insert courses
            for _, row in courses_df.iterrows():
                course = Course(
                    course_name=row["course_name"],
                    university_name=row["university_name"],
                    abbrv=row["abbrv"],
                    direct_entry_requirements=row["direct_entry_requirements"],
                    utme_requirements=row["utme_requirements"],
                    subjects=row["subjects"],
                )
                db.session.add(course)

            db.session.commit()
            logger.info("Courses data migrated successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise

        logger.info("Migration completed successfully.")


if __name__ == "__main__":
    migrate_to_sqlite()
