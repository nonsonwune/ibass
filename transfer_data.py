# transfer_data.py
from app import db, User, Comment, Vote, Feedback, University, Course

# Ensure you're connected to PostgreSQL via SQLALCHEMY_DATABASE_URI


# Export data from SQLite and import to PostgreSQL
def transfer():
    users = User.query.all()
    for user in users:
        db.session.add(user)
    comments = Comment.query.all()
    for comment in comments:
        db.session.add(comment)
    votes = Vote.query.all()
    for vote in votes:
        db.session.add(vote)
    feedbacks = Feedback.query.all()
    for feedback in feedbacks:
        db.session.add(feedback)
    universities = University.query.all()
    for uni in universities:
        db.session.add(uni)
    courses = Course.query.all()
    for course in courses:
        db.session.add(course)
    db.session.commit()


if __name__ == "__main__":
    transfer()
