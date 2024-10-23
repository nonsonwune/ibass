# transfer_data.py
import logging
import os
import sys
from app import app, User, Comment, Vote, Feedback, University, Course
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import multiprocessing
from multiprocessing import Pool, Value, Lock
from datetime import datetime

# Configure logging
LOG_FILE = "transfer_data.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s:%(message)s",
)

# Database URIs
SQLITE_DATABASE_PATH = "sqlite:///instance/university_courses.db"
POSTGRES_DATABASE_URI = "postgresql://nuf_user:AuoK48a6pVT0vJQhl5HKt2GG9nJhtGZJ@dpg-cs91krogph6c73bv1930-a.oregon-postgres.render.com/naija_uni_finder_db"

# Create engines and sessions
sqlite_engine = create_engine(SQLITE_DATABASE_PATH)
postgres_engine = create_engine(POSTGRES_DATABASE_URI)
SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)
sqlite_session = SQLiteSession()
postgres_session = PostgresSession()

# Create declarative base
Base = declarative_base()

# Mapping dictionaries
user_id_mapping = {}
comment_id_mapping = {}

# Global counter and lock for multiprocessing
counter = Value("i", 0)
counter_lock = Lock()


# Define TransferLog model
class TransferLog(Base):
    __tablename__ = "transfer_log"
    id = Column(Integer, primary_key=True)
    table_name = Column(String, nullable=False)
    last_transferred_id = Column(Integer, nullable=False)
    last_transfer_time = Column(DateTime, nullable=False)


# Function to get or create transfer log table
def get_or_create_transfer_log():
    Base.metadata.create_all(postgres_engine)
    return TransferLog


# Get TransferLog model
TransferLog = get_or_create_transfer_log()


def get_last_transferred_id(table_name):
    log = postgres_session.query(TransferLog).filter_by(table_name=table_name).first()
    return log.last_transferred_id if log else 0


def update_transfer_log(table_name, last_id):
    log = postgres_session.query(TransferLog).filter_by(table_name=table_name).first()
    if log:
        log.last_transferred_id = last_id
        log.last_transfer_time = datetime.utcnow()
    else:
        log = TransferLog(
            table_name=table_name,
            last_transferred_id=last_id,
            last_transfer_time=datetime.utcnow(),
        )
        postgres_session.add(log)
    postgres_session.commit()


def init_worker(cnt, lock):
    global counter, counter_lock
    counter = cnt
    counter_lock = lock


def process_chunk(chunk_data):
    func, chunk = chunk_data
    local_postgres_session = PostgresSession()
    try:
        for item in chunk:
            func(item, local_postgres_session)
        local_postgres_session.commit()
    except SQLAlchemyError as e:
        local_postgres_session.rollback()
        logging.error(f"Error processing chunk: {str(e)}")
    finally:
        local_postgres_session.close()


def transfer_with_multiprocessing(func, items, chunk_size=1000):
    chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
    chunk_data = [(func, chunk) for chunk in chunks]

    with Pool(
        processes=multiprocessing.cpu_count(),
        initializer=init_worker,
        initargs=(counter, counter_lock),
    ) as pool:
        pool.map(process_chunk, chunk_data)


def transfer_user(user, session):
    existing_user = session.query(User).filter_by(username=user.username).first()
    if existing_user:
        existing_user.email = user.email
        existing_user.password = user.password
        existing_user.is_admin = user.is_admin
        existing_user.score = user.score
        existing_user.is_verified = user.is_verified
        user_id_mapping[user.id] = existing_user.id
    else:
        new_user = User(
            username=user.username,
            email=user.email,
            password=user.password,
            is_admin=user.is_admin,
            score=user.score,
            is_verified=user.is_verified,
        )
        session.add(new_user)
        session.flush()
        user_id_mapping[user.id] = new_user.id

    with counter_lock:
        counter.value += 1
        if counter.value % 100 == 0:
            print(f"Processed {counter.value} users")


def transfer_users():
    try:
        last_id = get_last_transferred_id("users")
        users = (
            sqlite_session.query(User).filter(User.id > last_id).order_by(User.id).all()
        )
        total_users = len(users)
        print(f"Transferring {total_users} users")

        transfer_with_multiprocessing(transfer_user, users)

        if users:
            update_transfer_log("users", users[-1].id)
        logging.info("Users transferred successfully.")
        print("Users transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring users: {str(e)}")
        print(f"Error transferring users: {str(e)}")


def transfer_university(uni, session):
    existing_uni = (
        session.query(University).filter_by(university_name=uni.university_name).first()
    )
    if existing_uni:
        existing_uni.state = uni.state
        existing_uni.program_type = uni.program_type
    else:
        new_uni = University(
            university_name=uni.university_name,
            state=uni.state,
            program_type=uni.program_type,
        )
        session.add(new_uni)

    with counter_lock:
        counter.value += 1
        if counter.value % 10 == 0:
            print(f"Processed {counter.value} universities")


def transfer_universities():
    try:
        last_id = get_last_transferred_id("universities")
        universities = (
            sqlite_session.query(University)
            .filter(University.id > last_id)
            .order_by(University.id)
            .all()
        )
        total_unis = len(universities)
        print(f"Transferring {total_unis} universities")

        transfer_with_multiprocessing(transfer_university, universities)

        if universities:
            update_transfer_log("universities", universities[-1].id)
        logging.info("Universities transferred successfully.")
        print("Universities transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring universities: {str(e)}")
        print(f"Error transferring universities: {str(e)}")


def transfer_course(course, session):
    existing_course = (
        session.query(Course)
        .filter_by(
            course_name=course.course_name, university_name=course.university_name
        )
        .first()
    )
    if existing_course:
        existing_course.abbrv = course.abbrv
        existing_course.direct_entry_requirements = course.direct_entry_requirements
        existing_course.utme_requirements = course.utme_requirements
        existing_course.subjects = course.subjects
    else:
        university = (
            session.query(University)
            .filter_by(university_name=course.university_name)
            .first()
        )
        if not university:
            logging.warning(
                f"University not found for course: {course.course_name} - {course.university_name}"
            )
            return
        new_course = Course(
            course_name=course.course_name,
            university_name=course.university_name,
            abbrv=course.abbrv,
            direct_entry_requirements=course.direct_entry_requirements,
            utme_requirements=course.utme_requirements,
            subjects=course.subjects,
        )
        session.add(new_course)

    with counter_lock:
        counter.value += 1
        if counter.value % 100 == 0:
            print(f"Processed {counter.value} courses")


def transfer_courses():
    try:
        last_id = get_last_transferred_id("courses")
        courses = (
            sqlite_session.query(Course)
            .filter(Course.id > last_id)
            .order_by(Course.id)
            .all()
        )
        total_courses = len(courses)
        print(f"Transferring {total_courses} courses")

        transfer_with_multiprocessing(transfer_course, courses)

        if courses:
            update_transfer_log("courses", courses[-1].id)
        logging.info("Courses transferred successfully.")
        print("Courses transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring courses: {str(e)}")
        print(f"Error transferring courses: {str(e)}")


def transfer_comment(comment, session):
    new_user_id = user_id_mapping.get(comment.user_id)
    if new_user_id:
        existing_comment = (
            session.query(Comment)
            .filter_by(
                content=comment.content,
                date_posted=comment.date_posted,
                user_id=new_user_id,
            )
            .first()
        )
        if existing_comment:
            existing_comment.likes = comment.likes
            existing_comment.dislikes = comment.dislikes
            comment_id_mapping[comment.id] = existing_comment.id
        else:
            new_comment = Comment(
                content=comment.content,
                date_posted=comment.date_posted,
                user_id=new_user_id,
                likes=comment.likes,
                dislikes=comment.dislikes,
            )
            session.add(new_comment)
            session.flush()
            comment_id_mapping[comment.id] = new_comment.id
    else:
        logging.warning(f"Comment ID {comment.id} has no associated user.")

    with counter_lock:
        counter.value += 1
        if counter.value % 100 == 0:
            print(f"Processed {counter.value} comments")


def transfer_comments():
    try:
        last_id = get_last_transferred_id("comments")
        comments = (
            sqlite_session.query(Comment)
            .filter(Comment.id > last_id)
            .order_by(Comment.id)
            .all()
        )
        total_comments = len(comments)
        print(f"Transferring {total_comments} comments")

        transfer_with_multiprocessing(transfer_comment, comments)

        if comments:
            update_transfer_log("comments", comments[-1].id)
        logging.info("Comments transferred successfully.")
        print("Comments transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring comments: {str(e)}")
        print(f"Error transferring comments: {str(e)}")


def transfer_vote(vote, session):
    new_user_id = user_id_mapping.get(vote.user_id)
    new_comment_id = comment_id_mapping.get(vote.comment_id)
    if new_user_id and new_comment_id:
        existing_vote = (
            session.query(Vote)
            .filter_by(user_id=new_user_id, comment_id=new_comment_id)
            .first()
        )
        if existing_vote:
            existing_vote.vote_type = vote.vote_type
            existing_vote.timestamp = vote.timestamp
        else:
            new_vote = Vote(
                user_id=new_user_id,
                comment_id=new_comment_id,
                vote_type=vote.vote_type,
                timestamp=vote.timestamp,
            )
            session.add(new_vote)
    else:
        logging.warning(
            f"Vote ID {vote.id} references invalid user_id {vote.user_id} or comment_id {vote.comment_id}."
        )

    with counter_lock:
        counter.value += 1
        if counter.value % 100 == 0:
            print(f"Processed {counter.value} votes")


def transfer_votes():
    try:
        last_id = get_last_transferred_id("votes")
        votes = (
            sqlite_session.query(Vote).filter(Vote.id > last_id).order_by(Vote.id).all()
        )
        total_votes = len(votes)
        print(f"Transferring {total_votes} votes")

        transfer_with_multiprocessing(transfer_vote, votes)

        if votes:
            update_transfer_log("votes", votes[-1].id)
        logging.info("Votes transferred successfully.")
        print("Votes transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring votes: {str(e)}")
        print(f"Error transferring votes: {str(e)}")


def transfer_feedback_item(feedback, session):
    new_user_id = user_id_mapping.get(feedback.user_id) if feedback.user_id else None
    existing_feedback = (
        session.query(Feedback)
        .filter_by(
            name=feedback.name,
            email=feedback.email,
            subject=feedback.subject,
            date_submitted=feedback.date_submitted,
        )
        .first()
    )
    if existing_feedback:
        existing_feedback.message = feedback.message
        existing_feedback.user_id = new_user_id
    else:
        new_feedback = Feedback(
            name=feedback.name,
            email=feedback.email,
            subject=feedback.subject,
            message=feedback.message,
            date_submitted=feedback.date_submitted,
            user_id=new_user_id,
        )
        session.add(new_feedback)

    with counter_lock:
        counter.value += 1
        if counter.value % 100 == 0:
            print(f"Processed {counter.value} feedback items")


def transfer_feedback():
    try:
        last_id = get_last_transferred_id("feedback")
        feedbacks = (
            sqlite_session.query(Feedback)
            .filter(Feedback.id > last_id)
            .order_by(Feedback.id)
            .all()
        )
        total_feedbacks = len(feedbacks)
        print(f"Transferring {total_feedbacks} feedback items")

        transfer_with_multiprocessing(transfer_feedback_item, feedbacks)

        if feedbacks:
            update_transfer_log("feedback", feedbacks[-1].id)
        logging.info("Feedbacks transferred successfully.")
        print("Feedbacks transferred successfully.")
    except Exception as e:
        logging.error(f"Error transferring feedbacks: {str(e)}")
        print(f"Error transferring feedbacks: {str(e)}")


if __name__ == "__main__":
    with app.app_context():
        try:
            transfer_functions = [
                transfer_users,
                transfer_universities,
                transfer_courses,
                transfer_comments,
                transfer_votes,
                transfer_feedback,
            ]

            for func in transfer_functions:
                try:
                    func()
                except Exception as e:
                    logging.error(f"Error in {func.__name__}: {str(e)}")
                    print(f"Error in {func.__name__}: {str(e)}")
                    continue  # Continue with the next transfer function
        finally:
            sqlite_session.close()
            postgres_session.close()

    print("Transfer process completed.")
