# migration_db_local_postgres.py
import pandas as pd
from app_backup import db, University, Course, app
import logging
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    with app.app_context():
        try:
            # Drop all existing tables
            db.drop_all()
            logger.info("Dropped all existing tables.")

            # Create all tables based on the current models
            db.create_all()
            logger.info("Database tables created successfully.")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

def clear_database():
    with app.app_context():
        try:
            # Clear data from tables
            db.session.query(Course).delete()
            db.session.query(University).delete()
            db.session.commit()
            logger.info("Database cleared successfully.")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error clearing database: {str(e)}")
            raise

def migrate_data():
    with app.app_context():
        try:
            # Read data from CSV files
            universities_df = pd.read_csv("universities_updated.csv")
            courses_df = pd.read_csv("courses.csv")

            # Insert universities
            for _, row in universities_df.iterrows():
                existing_university = University.query.filter_by(
                    university_name=row["university_name"]
                ).first()
                
                if not existing_university:
                    # Handle NaN values
                    website = row.get("website")
                    if pd.isna(website):
                        website = None

                    established = row.get("established")
                    if pd.isna(established):
                        established = None
                    else:
                        # Ensure established is an integer
                        try:
                            established = int(float(established))
                        except (ValueError, TypeError):
                            established = None

                    university = University(
                        university_name=row["university_name"],
                        state=row["state"],
                        program_type=row["program_type"],
                        website=website,
                        established=established
                    )
                    db.session.add(university)
                    logger.info(f"Added new university: {row['university_name']}")
                else:
                    # Update existing university
                    # Handle NaN values
                    website = row.get("website")
                    if pd.isna(website):
                        website = None

                    established = row.get("established")
                    if pd.isna(established):
                        established = None
                    else:
                        try:
                            established = int(float(established))
                        except (ValueError, TypeError):
                            established = None

                    existing_university.website = website
                    existing_university.established = established
                    logger.info(f"Updated existing university: {row['university_name']}")
            
            # Commit university data
            db.session.commit()
            logger.info("Universities data migrated successfully.")

            # Insert courses
            for _, row in courses_df.iterrows():
                try:
                    # Check if the university exists
                    university = University.query.filter_by(
                        university_name=row["university_name"]
                    ).first()
                    
                    if not university:
                        logger.warning(
                            f"University not found for course: {row['course_name']} at {row['university_name']}"
                        )
                        continue
                        
                    existing_course = Course.query.filter_by(
                        course_name=row["course_name"],
                        university_name=row["university_name"],
                    ).first()
                    
                    if not existing_course:
                        # Handle NaN values for course fields
                        abbrv = row.get("abbrv")
                        if pd.isna(abbrv):
                            abbrv = None

                        direct_entry_requirements = row.get("direct_entry_requirements")
                        if pd.isna(direct_entry_requirements):
                            direct_entry_requirements = None

                        utme_requirements = row.get("utme_requirements")
                        if pd.isna(utme_requirements):
                            utme_requirements = None

                        subjects = row.get("subjects")
                        if pd.isna(subjects):
                            subjects = None

                        course = Course(
                            course_name=row["course_name"],
                            university_name=row["university_name"],
                            abbrv=abbrv,
                            direct_entry_requirements=direct_entry_requirements,
                            utme_requirements=utme_requirements,
                            subjects=subjects,
                        )
                        db.session.add(course)
                        logger.info(
                            f"Added new course: {row['course_name']} at {row['university_name']}"
                        )
                    else:
                        logger.info(
                            f"Course '{row['course_name']}' at '{row['university_name']}' already exists. Skipping."
                        )
                    
                    # Commit after each course
                    db.session.commit()
                    
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.error(f"Error adding course {row['course_name']}: {str(e)}")
                    continue

            logger.info("Migration completed successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    # Initialize the database
    init_database()
    
    user_input = input(
        "Do you want to clear the existing data before migration? (yes/no): "
    ).lower()
    if user_input == "yes":
        clear_database()
    migrate_data()
