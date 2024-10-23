import logging
import sys
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

# ----------------------------- Configuration -----------------------------

# Configure logging
LOG_FILE = "clear_postgres.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s %(levelname)s:%(message)s",
)

# Database URI (Ensure this matches your PostgreSQL configuration)
POSTGRES_DATABASE_URI = "postgresql://nuf_user:AuoK48a6pVT0vJQhl5HKt2GG9nJhtGZJ@dpg-cs91krogph6c73bv1930-a.oregon-postgres.render.com/naija_uni_finder_db"

# ----------------------------- Database Setup -----------------------------

# Create engine and session
try:
    postgres_engine = create_engine(POSTGRES_DATABASE_URI)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()
    logging.debug("Successfully connected to PostgreSQL database.")
except Exception as e:
    logging.error(f"Error connecting to PostgreSQL database: {str(e)}")
    sys.exit(1)

# Create declarative base
Base = declarative_base()

# ----------------------------- Models -----------------------------

# Define only the necessary models to reflect the database schema

class University(Base):
    __tablename__ = "university"

    id = Column(Integer, primary_key=True)
    university_name = Column(String(256), unique=True, nullable=False)
    state = Column(String(50), nullable=False)
    program_type = Column(String(50), nullable=False)
    website = Column(String(255))
    established = Column(Integer)
    # Relationships (optional, not necessary for deletion)
    courses = relationship("Course", backref="university", cascade="all, delete-orphan")

class Course(Base):
    __tablename__ = "course"

    id = Column(Integer, primary_key=True)
    course_name = Column(String(256), nullable=False)
    university_name = Column(String(256), ForeignKey("university.university_name"), nullable=False)
    abbrv = Column(Text)
    direct_entry_requirements = Column(Text)
    utme_requirements = Column(Text)
    subjects = Column(Text)
    # Relationships (optional, not necessary for deletion)

# ----------------------------- Clearing Functionality -----------------------------

def clear_tables():
    """
    Clears the 'course' and 'university' tables in PostgreSQL in the correct order to respect foreign key constraints.
    """
    try:
        logging.info("Starting to clear PostgreSQL tables: 'course' and 'university'.")

        # Define the order of deletion based on foreign key dependencies
        # 'course' depends on 'university', so truncate 'course' first
        tables_in_order = [
            Course.__tablename__,
            University.__tablename__,
        ]

        for table in tables_in_order:
            # Wrap the raw SQL with text()
            truncate_stmt = text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
            postgres_session.execute(truncate_stmt)
            logging.debug(f"Truncated table '{table}' and reset its identity.")

        postgres_session.commit()
        logging.info("Successfully cleared 'course' and 'university' tables.")
        print("Successfully cleared 'course' and 'university' tables.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error clearing tables: {str(e)}")
        print(f"Error clearing tables: {str(e)}")
        sys.exit(1)
    except Exception as e:
        postgres_session.rollback()
        logging.error(f"Unexpected error: {str(e)}")
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        postgres_session.close()
        logging.debug("PostgreSQL session closed.")

# ----------------------------- Main Execution -----------------------------

def main():
    clear_tables()

if __name__ == "__main__":
    main()
