# transfer_data.py
import logging
import os
import sys
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import SQLAlchemyError

import multiprocessing
from multiprocessing import Pool, Value, Lock, Manager

# ----------------------------- Configuration -----------------------------

# Configure logging
LOG_FILE = "transfer_data.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s %(levelname)s:%(message)s",
)

# Database URIs
SQLITE_DATABASE_PATH = "sqlite:///instance/university_courses.db"
POSTGRES_DATABASE_URI = (
    "postgresql://nuf_user:AuoK48a6pVT0vJQhl5HKt2GG9nJhtGZJ@"
    "dpg-cs91krogph6c73bv1930-a.oregon-postgres.render.com/naija_uni_finder_db"
)

# ----------------------------- Database Setup -----------------------------

# Create engines
try:
    sqlite_engine = create_engine(SQLITE_DATABASE_PATH)
    postgres_engine = create_engine(POSTGRES_DATABASE_URI)
    logging.debug("Successfully created database engines.")
except Exception as e:
    logging.error(f"Error creating database engines: {str(e)}")
    sys.exit(1)

# Create session factories
SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

# Instantiate a PostgreSQL session for main process operations (TransferLog)
postgres_session = PostgresSession()

# Create declarative base
Base = declarative_base()

# ----------------------------- Models -----------------------------

# TransferLog model to keep track of last transferred IDs
class TransferLog(Base):
    __tablename__ = "transfer_log"
    id = Column(Integer, primary_key=True)
    table_name = Column(String, nullable=False, unique=True)
    last_transferred_id = Column(Integer, nullable=False)
    last_transfer_time = Column(DateTime, nullable=False)

# User model
class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(20), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    is_admin = Column(Integer, default=0)  # Assuming Boolean stored as Integer
    is_verified = Column(Integer, default=0)  # Assuming Boolean stored as Integer
    score = Column(Integer, default=0, nullable=False, index=True)
    # Relationships (optional, not necessary for deletion)
    comments = relationship(
        "Comment", backref="author", cascade="all, delete-orphan"
    )
    votes = relationship(
        "Vote", backref="voter", cascade="all, delete-orphan"
    )
    feedback = relationship(
        "Feedback", backref="user", cascade="all, delete-orphan"
    )
    bookmarks = relationship(
        "Bookmark", backref="user", cascade="all, delete-orphan"
    )

# University model
class University(Base):
    __tablename__ = "university"

    id = Column(Integer, primary_key=True)
    university_name = Column(String(256), unique=True, nullable=False)
    state = Column(String(50), nullable=False)
    program_type = Column(String(50), nullable=False)
    website = Column(String(255))
    established = Column(Integer)
    # Relationships (optional, not necessary for deletion)
    courses = relationship(
        "Course", backref="university", cascade="all, delete-orphan"
    )
    bookmarks = relationship(
        "Bookmark", backref="university", cascade="all, delete-orphan"
    )

# Course model
class Course(Base):
    __tablename__ = "course"

    id = Column(Integer, primary_key=True)
    course_name = Column(String(256), nullable=False)
    university_name = Column(
        String(256),
        ForeignKey("university.university_name"),
        nullable=False,
    )
    abbrv = Column(Text)
    direct_entry_requirements = Column(Text)
    utme_requirements = Column(Text)
    subjects = Column(Text)

# Comment model
class Comment(Base):
    __tablename__ = "comment"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    date_posted = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    votes = relationship(
        "Vote", backref="comment", cascade="all, delete-orphan"
    )

# Vote model
class Vote(Base):
    __tablename__ = "vote"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    comment_id = Column(
        Integer, ForeignKey("comment.id", ondelete="CASCADE"), nullable=False
    )
    vote_type = Column(String(10), nullable=False)  # 'like' or 'dislike'
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="user_comment_uc"),
    )

# Feedback model
class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    date_submitted = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

# Bookmark model
class Bookmark(Base):
    __tablename__ = "bookmark"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    university_id = Column(
        Integer, ForeignKey("university.id", ondelete="CASCADE"), nullable=False
    )
    course_id = Column(
        Integer, ForeignKey("course.id", ondelete="CASCADE"), nullable=True
    )
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)

# ----------------------------- Global Variables for Shared Objects -----------------------------

# Global variables for shared objects
shared_user_id_mapping = None
shared_counter = None
shared_counter_lock = None

# ----------------------------- Pool Initializer -----------------------------

def pool_initializer(user_id_mapping_, counter_, counter_lock_):
    """
    Initializer function for each pool worker.
    Sets global variables to shared objects.
    """
    global shared_user_id_mapping
    global shared_counter
    global shared_counter_lock
    shared_user_id_mapping = user_id_mapping_
    shared_counter = counter_
    shared_counter_lock = counter_lock_

# ----------------------------- Utility Functions -----------------------------

def get_or_create_transfer_log():
    """
    Ensures that the TransferLog table exists in PostgreSQL.
    """
    try:
        Base.metadata.create_all(postgres_engine)
        logging.debug("Ensured TransferLog table exists in PostgreSQL.")
    except Exception as e:
        logging.error(f"Error creating TransferLog table: {str(e)}")
        sys.exit(1)

def get_last_transferred_id(table_name, session):
    """
    Retrieves the last transferred ID for a given table from TransferLog.
    If no entry exists, returns 0.
    """
    try:
        log_entry = session.query(TransferLog).filter_by(table_name=table_name).first()
        if log_entry:
            logging.debug(
                f"Last transferred ID for '{table_name}': {log_entry.last_transferred_id}"
            )
            return log_entry.last_transferred_id
        else:
            logging.debug(
                f"No TransferLog entry found for '{table_name}'. Starting from ID 0."
            )
            return 0
    except SQLAlchemyError as e:
        logging.error(
            f"Error retrieving last transferred ID for '{table_name}': {str(e)}"
        )
        sys.exit(1)

def update_transfer_log(table_name, last_id, session):
    """
    Updates the TransferLog with the last transferred ID for a given table.
    If no entry exists, creates one.
    """
    try:
        log_entry = session.query(TransferLog).filter_by(table_name=table_name).first()
        if log_entry:
            log_entry.last_transferred_id = last_id
            log_entry.last_transfer_time = datetime.utcnow()
            logging.debug(f"Updated TransferLog for '{table_name}' with ID {last_id}.")
        else:
            log_entry = TransferLog(
                table_name=table_name,
                last_transferred_id=last_id,
                last_transfer_time=datetime.utcnow(),
            )
            session.add(log_entry)
            logging.debug(
                f"Created TransferLog entry for '{table_name}' with ID {last_id}."
            )
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logging.error(
            f"Error updating TransferLog for '{table_name}': {str(e)}"
        )
        sys.exit(1)

# ----------------------------- Worker Functions -----------------------------

def process_user_chunk(chunk):
    """
    Worker function to process a chunk of users.
    Accesses shared objects via global variables.
    """
    global shared_user_id_mapping
    global shared_counter
    global shared_counter_lock

    session = PostgresSession()
    try:
        for user in chunk:
            existing_user = session.query(User).filter_by(username=user.username).first()
            if existing_user:
                # Update existing user
                existing_user.email = user.email
                existing_user.password = user.password
                existing_user.is_admin = user.is_admin
                existing_user.score = user.score
                existing_user.is_verified = user.is_verified
                shared_user_id_mapping[user.id] = existing_user.id
                logging.debug(f"Updated user '{user.username}' (ID: {user.id}).")
            else:
                # Insert new user
                new_user = User(
                    username=user.username,
                    email=user.email,
                    password=user.password,
                    is_admin=user.is_admin,
                    score=user.score,
                    is_verified=user.is_verified,
                )
                session.add(new_user)
                session.flush()  # Assigns an ID to new_user
                shared_user_id_mapping[user.id] = new_user.id
                logging.debug(f"Inserted new user '{user.username}' (ID: {user.id}).")
            
            # Update counter
            with shared_counter_lock:
                shared_counter.value += 1
                if shared_counter.value % 100 == 0:
                    print(f"Processed {shared_counter.value} users")
    except Exception as e:
        logging.error(f"Error processing user chunk: {str(e)}")
    finally:
        session.commit()
        session.close()

def process_university_chunk(chunk):
    """
    Worker function to process a chunk of universities.
    Accesses shared objects via global variables.
    """
    global shared_counter
    global shared_counter_lock

    session = PostgresSession()
    try:
        for uni in chunk:
            existing_uni = session.query(University).filter_by(university_name=uni.university_name).first()
            if existing_uni:
                # Update existing university
                existing_uni.state = uni.state
                existing_uni.program_type = uni.program_type
                existing_uni.website = uni.website
                existing_uni.established = uni.established
                logging.debug(f"Updated university '{uni.university_name}' (ID: {uni.id}).")
            else:
                # Insert new university
                new_uni = University(
                    university_name=uni.university_name,
                    state=uni.state,
                    program_type=uni.program_type,
                    website=uni.website,
                    established=uni.established,
                )
                session.add(new_uni)
                logging.debug(f"Inserted new university '{uni.university_name}' (ID: {uni.id}).")
            
            # Update counter
            with shared_counter_lock:
                shared_counter.value += 1
                if shared_counter.value % 10 == 0:
                    print(f"Processed {shared_counter.value} universities")
    except Exception as e:
        logging.error(f"Error processing university chunk: {str(e)}")
    finally:
        session.commit()
        session.close()

def process_course_chunk(chunk):
    """
    Worker function to process a chunk of courses.
    Accesses shared objects via global variables.
    """
    global shared_counter
    global shared_counter_lock

    session = PostgresSession()
    try:
        for course in chunk:
            existing_course = session.query(Course).filter_by(
                course_name=course.course_name,
                university_name=course.university_name
            ).first()
            if existing_course:
                # Update existing course
                existing_course.abbrv = course.abbrv
                existing_course.direct_entry_requirements = course.direct_entry_requirements
                existing_course.utme_requirements = course.utme_requirements
                existing_course.subjects = course.subjects
                logging.debug(f"Updated course '{course.course_name}' at '{course.university_name}' (ID: {course.id}).")
            else:
                # Insert new course
                # Ensure the referenced university exists
                university = session.query(University).filter_by(university_name=course.university_name).first()
                if not university:
                    logging.warning(
                        f"University not found for course: {course.course_name} - {course.university_name}"
                    )
                    continue  # Skip inserting this course
                new_course = Course(
                    course_name=course.course_name,
                    university_name=course.university_name,
                    abbrv=course.abbrv,
                    direct_entry_requirements=course.direct_entry_requirements,
                    utme_requirements=course.utme_requirements,
                    subjects=course.subjects,
                )
                session.add(new_course)
                logging.debug(f"Inserted new course '{course.course_name}' at '{course.university_name}' (ID: {course.id}).")
            
            # Update counter
            with shared_counter_lock:
                shared_counter.value += 1
                if shared_counter.value % 100 == 0:
                    print(f"Processed {shared_counter.value} courses")
    except Exception as e:
        logging.error(f"Error processing course chunk: {str(e)}")
    finally:
        session.commit()
        session.close()

# ----------------------------- Multiprocessing Setup -----------------------------

def transfer_with_multiprocessing(func, chunk_size, items, shared_dicts, counter, counter_lock):
    """
    Handles multiprocessing for transferring data.
    
    :param func: Worker function to process a chunk.
    :param chunk_size: Number of items per chunk.
    :param items: List of items to process.
    :param shared_dicts: Dictionary containing shared data between processes.
    :param counter: Shared counter for progress tracking.
    :param counter_lock: Lock for the shared counter.
    """
    # Split items into chunks
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    
    # Define initializer and its arguments
    if func == process_user_chunk:
        initializer = pool_initializer
        initargs = (shared_dicts['user_id_mapping'], counter, counter_lock)
    else:
        initializer = pool_initializer
        initargs = (None, counter, counter_lock)  # No user_id_mapping for other functions
    
    # Use Pool with initializer
    with Pool(
        processes=multiprocessing.cpu_count(),
        initializer=initializer,
        initargs=initargs
    ) as pool:
        pool.map(func, chunks)

# ----------------------------- Transfer Functions -----------------------------

def transfer_users(shared_dicts, counter, counter_lock):
    """
    Transfers users from SQLite to PostgreSQL using multiprocessing.
    """
    try:
        last_id = get_last_transferred_id("users", postgres_session)
        session = SQLiteSession()
        users = (
            session.query(User)
            .filter(User.id > last_id)
            .order_by(User.id)
            .all()
        )
        session.close()
        total_users = len(users)
        print(f"Transferring {total_users} users")
        logging.info(f"Starting transfer of {total_users} users.")

        if total_users == 0:
            print("No new users to transfer.")
            return

        # Use multiprocessing to transfer users
        transfer_with_multiprocessing(
            process_user_chunk,
            chunk_size=1000,
            items=users,
            shared_dicts=shared_dicts,
            counter=counter,
            counter_lock=counter_lock
        )

        # Update TransferLog
        if users:
            update_transfer_log("users", users[-1].id, postgres_session)

        logging.info("Users transferred successfully.")
        print("Users transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring users: {str(e)}")
        print(f"Error transferring users: {str(e)}")


def transfer_universities(shared_dicts, counter, counter_lock):
    """
    Transfers universities from SQLite to PostgreSQL using multiprocessing.
    """
    try:
        last_id = get_last_transferred_id("universities", postgres_session)
        session = SQLiteSession()
        universities = (
            session.query(University)
            .filter(University.id > last_id)
            .order_by(University.id)
            .all()
        )
        session.close()
        total_unis = len(universities)
        print(f"Transferring {total_unis} universities")
        logging.info(f"Starting transfer of {total_unis} universities.")

        if total_unis == 0:
            print("No new universities to transfer.")
            return

        # Use multiprocessing to transfer universities
        transfer_with_multiprocessing(
            process_university_chunk,
            chunk_size=1000,
            items=universities,
            shared_dicts=shared_dicts,
            counter=counter,
            counter_lock=counter_lock
        )

        # Update TransferLog
        if universities:
            update_transfer_log("universities", universities[-1].id, postgres_session)

        logging.info("Universities transferred successfully.")
        print("Universities transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring universities: {str(e)}")
        print(f"Error transferring universities: {str(e)}")


def transfer_courses(shared_dicts, counter, counter_lock):
    """
    Transfers courses from SQLite to PostgreSQL using multiprocessing.
    """
    try:
        last_id = get_last_transferred_id("courses", postgres_session)
        session = SQLiteSession()
        courses = (
            session.query(Course)
            .filter(Course.id > last_id)
            .order_by(Course.id)
            .all()
        )
        session.close()
        total_courses = len(courses)
        print(f"Transferring {total_courses} courses")
        logging.info(f"Starting transfer of {total_courses} courses.")

        if total_courses == 0:
            print("No new courses to transfer.")
            return

        # Use multiprocessing to transfer courses
        transfer_with_multiprocessing(
            process_course_chunk,
            chunk_size=1000,
            items=courses,
            shared_dicts=shared_dicts,
            counter=counter,
            counter_lock=counter_lock
        )

        # Update TransferLog
        if courses:
            update_transfer_log("courses", courses[-1].id, postgres_session)

        logging.info("Courses transferred successfully.")
        print("Courses transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring courses: {str(e)}")
        print(f"Error transferring courses: {str(e)}")

# Add similar transfer functions for comments, votes, feedback as needed

# ----------------------------- Main Execution -----------------------------

def main():
    # Ensure TransferLog table exists
    get_or_create_transfer_log()

    # Initialize multiprocessing Manager
    manager = Manager()

    # Shared dictionaries
    shared_dicts = {
        'user_id_mapping': manager.dict(),
        # Add other shared dictionaries like 'comment_id_mapping' if needed
    }

    # Shared counter and lock
    counter = Value('i', 0)
    counter_lock = Lock()

    # Define transfer functions and their required shared data
    transfer_functions = [
        transfer_users,
        transfer_universities,
        transfer_courses,
        # Add functions for comments, votes, feedback as needed
    ]

    # Iterate through transfer functions and execute them
    for func in transfer_functions:
        try:
            func(shared_dicts, counter, counter_lock)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            print(f"Error in {func.__name__}: {str(e)}")
            continue  # Continue with the next transfer function

    print("Transfer process completed successfully.")
    logging.info("Transfer process completed successfully.")

    # Close PostgreSQL session
    postgres_session.close()

if __name__ == "__main__":
    main()
