# transfer_data.py
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import User, Comment, Vote, Feedback, University, Course, db
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

# Configure logging
# Define an absolute path for the log file
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transfer_data.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s:%(message)s",
)

# Define the paths to your SQLite and PostgreSQL databases
SQLITE_DATABASE_PATH = "sqlite:///instance/university_courses.db"
POSTGRES_DATABASE_URI = (
    "postgresql://ibass_user:your_password@localhost/university_courses"
)

# Create engines for both databases
sqlite_engine = create_engine(SQLITE_DATABASE_PATH)
postgres_engine = create_engine(POSTGRES_DATABASE_URI)

# Create session makers for both databases
SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

# Create sessions
sqlite_session = SQLiteSession()
postgres_session = PostgresSession()

# Mapping dictionaries
user_id_mapping = {}
comment_id_mapping = {}


def transfer_users():
    try:
        users = sqlite_session.query(User).all()
        for user in users:
            existing_user = (
                postgres_session.query(User).filter_by(username=user.username).first()
            )
            if not existing_user:
                new_user = User(
                    username=user.username,
                    email=user.email,
                    password=user.password,  # Assuming already hashed
                    is_admin=user.is_admin,
                    score=user.score,
                    is_verified=user.is_verified,  # Add this line
                )
                postgres_session.add(new_user)
                postgres_session.flush()  # Assign ID
                user_id_mapping[user.id] = new_user.id
                logging.debug(
                    f"Transferred user '{user.username}' with new ID {new_user.id}."
                )
            else:
                user_id_mapping[user.id] = existing_user.id
                logging.debug(
                    f"User '{user.username}' already exists with ID {existing_user.id}."
                )
        postgres_session.commit()
        logging.info("Users transferred successfully.")
        print("Users transferred successfully.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error transferring users: {str(e)}")
        print(f"Error transferring users: {str(e)}")


def transfer_universities():
    try:
        universities = sqlite_session.query(University).all()
        for uni in universities:
            existing_uni = (
                postgres_session.query(University)
                .filter_by(university_name=uni.university_name)
                .first()
            )
            if not existing_uni:
                new_uni = University(
                    university_name=uni.university_name,
                    state=uni.state,
                    program_type=uni.program_type,
                )
                postgres_session.add(new_uni)
                logging.debug(f"Transferred university '{uni.university_name}'.")
        postgres_session.commit()
        logging.info("Universities transferred successfully.")
        print("Universities transferred successfully.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error transferring universities: {e}")
        print(f"Error transferring universities: {e}")


def transfer_courses():
    try:
        courses = sqlite_session.query(Course).all()
        for course in courses:
            existing_course = (
                postgres_session.query(Course)
                .filter_by(
                    course_name=course.course_name,
                    university_name=course.university_name,
                )
                .first()
            )
            if not existing_course:
                new_course = Course(
                    course_name=course.course_name,
                    university_name=course.university_name,
                    abbrv=course.abbrv,
                    direct_entry_requirements=course.direct_entry_requirements,
                    utme_requirements=course.utme_requirements,
                    subjects=course.subjects,
                )
                postgres_session.add(new_course)
                postgres_session.flush()  # Assign ID
                logging.debug(
                    f"Transferred course '{course.course_name}' with new ID {new_course.id}."
                )
        postgres_session.commit()
        logging.info("Courses transferred successfully.")
        print("Courses transferred successfully.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error transferring courses: {e}")
        print(f"Error transferring courses: {e}")


def transfer_comments():
    try:
        comments = sqlite_session.query(Comment).all()
        for comment in comments:
            new_user_id = user_id_mapping.get(comment.user_id)
            if new_user_id:
                new_comment = Comment(
                    content=comment.content,
                    date_posted=comment.date_posted,
                    user_id=new_user_id,
                    likes=comment.likes,
                    dislikes=comment.dislikes,
                )
                postgres_session.add(new_comment)
                postgres_session.flush()  # Assign ID
                comment_id_mapping[comment.id] = new_comment.id
                logging.debug(
                    f"Transferred comment ID {comment.id} to new ID {new_comment.id}."
                )
            else:
                logging.warning(f"Comment ID {comment.id} has no associated user.")
        postgres_session.commit()
        logging.info("Comments transferred successfully.")
        print("Comments transferred successfully.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error transferring comments: {e}")
        print(f"Error transferring comments: {e}")


def transfer_votes():
    try:
        votes = sqlite_session.query(Vote).all()
        for vote in votes:
            new_user_id = user_id_mapping.get(vote.user_id)
            new_comment_id = comment_id_mapping.get(vote.comment_id)
            if new_user_id and new_comment_id:
                existing_vote = (
                    postgres_session.query(Vote)
                    .filter_by(
                        user_id=new_user_id,
                        comment_id=new_comment_id,
                        vote_type=vote.vote_type,
                    )
                    .first()
                )
                if not existing_vote:
                    new_vote = Vote(
                        user_id=new_user_id,
                        comment_id=new_comment_id,
                        vote_type=vote.vote_type,
                        timestamp=vote.timestamp,
                    )
                    postgres_session.add(new_vote)
                    logging.debug(f"Transferred vote ID {vote.id} to new vote.")
            else:
                logging.warning(
                    f"Vote ID {vote.id} references invalid user_id {vote.user_id} or comment_id {vote.comment_id}."
                )
        postgres_session.commit()
        logging.info("Votes transferred successfully.")
        print("Votes transferred successfully.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error transferring votes: {e}")
        print(f"Error transferring votes: {e}")


def transfer_feedback():
    try:
        feedbacks = sqlite_session.query(Feedback).all()
        for feedback in feedbacks:
            new_user_id = (
                user_id_mapping.get(feedback.user_id) if feedback.user_id else None
            )
            new_feedback = Feedback(
                name=feedback.name,
                email=feedback.email,
                subject=feedback.subject,
                message=feedback.message,
                date_submitted=feedback.date_submitted,
                user_id=new_user_id,
            )
            postgres_session.add(new_feedback)
            logging.debug(f"Transferred feedback ID {feedback.id}.")
        postgres_session.commit()
        logging.info("Feedbacks transferred successfully.")
        print("Feedbacks transferred successfully.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error transferring feedbacks: {e}")
        print(f"Error transferring feedbacks: {e}")


if __name__ == "__main__":
    try:
        transfer_users()
        transfer_universities()
        transfer_courses()
        transfer_comments()
        transfer_votes()
        transfer_feedback()
    finally:
        sqlite_session.close()
        postgres_session.close()
