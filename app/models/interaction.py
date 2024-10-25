# app/models/interaction.py
from datetime import datetime
from .base import BaseModel
from ..extensions import db

class Comment(BaseModel):
    __tablename__ = 'comments'
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    votes = db.relationship('Vote', backref='comment', lazy=True, cascade='all, delete-orphan')

    # Add index for likes and dislikes columns
    __table_args__ = (
        db.Index('idx_comments_user_scores', 'user_id', 'likes', 'dislikes'),
    )

    @property
    def score(self):
        return self.likes - self.dislikes

class Vote(BaseModel):
    __tablename__ = 'votes'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', name='fk_vote_user_id_user'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id', ondelete='CASCADE', 
                                                    name='fk_vote_comment_id_comment'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'comment_id', name='user_comment_uc'),
        db.Index('idx_votes_user_comment', 'user_id', 'comment_id'),
    )


class Bookmark(BaseModel):
    __tablename__ = 'bookmarks'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('universities.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=True)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)