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
                existing_university = University.query.filter_by(
                    university_name=row["university_name"]
                ).first()
                if not existing_university:
                    university = University(
                        university_name=row["university_name"],
                        state=row["state"],
                        program_type=row["program_type"],
                    )
                    db.session.add(university)
                    logger.info(f"Added new university: {row['university_name']}")
                else:
                    logger.info(
                        f"University '{row['university_name']}' already exists. Skipping."
                    )

            db.session.commit()
            logger.info("Universities data migrated successfully.")

            # Insert courses
            for _, row in courses_df.iterrows():
                existing_course = Course.query.filter_by(
                    course_name=row["course_name"],
                    university_name=row["university_name"],
                ).first()
                if not existing_course:
                    course = Course(
                        course_name=row["course_name"],
                        university_name=row["university_name"],
                        abbrv=row["abbrv"],
                        direct_entry_requirements=row["direct_entry_requirements"],
                        utme_requirements=row["utme_requirements"],
                        subjects=row["subjects"],
                    )
                    db.session.add(course)
                    logger.info(
                        f"Added new course: {row['course_name']} at {row['university_name']}"
                    )
                else:
                    logger.info(
                        f"Course '{row['course_name']}' at '{row['university_name']}' already exists. Skipping."
                    )

            db.session.commit()
            logger.info("Courses data migrated successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise

        logger.info("Migration completed successfully.")


def clear_database():
    with app.app_context():
        try:
            # Remove all records from Course and University tables
            Course.query.delete()
            University.query.delete()
            db.session.commit()
            logger.info("Database cleared successfully.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing database: {str(e)}")
            raise


if __name__ == "__main__":
    user_input = input(
        "Do you want to clear the existing data before migration? (yes/no): "
    ).lower()
    if user_input == "yes":
        clear_database()
    migrate_to_sqlite()
