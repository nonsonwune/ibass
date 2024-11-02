# app/models/interaction.py
from datetime import datetime
from .base import BaseModel
from ..extensions import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func, select

class Comment(BaseModel):
    __tablename__ = 'comment'
    
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    
    # Relationship definitions
    replies = db.relationship(
        'Comment',
        backref=db.backref(
            'parent', 
            remote_side='Comment.id'
        ),
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Comment.date_posted.asc()'
    )
    
    votes = db.relationship(
        'Vote', 
        backref='comment',
        lazy=True,
        cascade='all, delete-orphan'
    )
    
    __table_args__ = (
        db.Index('idx_comment_parent_date', 'parent_id', 'date_posted'),
    )
    
    @property
    def score(self):
        return self.likes - self.dislikes
    
    @hybrid_property
    def reply_count(self):
        return self.replies.count()
    
    @reply_count.expression
    def reply_count(cls):
        return (
            select([func.count(Comment.id)])
            .where(Comment.parent_id == cls.id)
            .correlate_except(Comment)
            .scalar_subquery()
            .label('reply_count')
        )

class Vote(BaseModel):
    __tablename__ = 'vote'
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'comment_id', name='user_comment_uc'),
        db.CheckConstraint(
            vote_type.in_(['like', 'dislike']),
            name='vote_type_check'
        )
    )

class Bookmark(BaseModel):
    __tablename__ = 'bookmark'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=True)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Add relationships
    university = db.relationship('University', backref=db.backref('bookmarks', lazy=True))
    course = db.relationship('Course', backref=db.backref('bookmarks', lazy=True))
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'university_id', 'course_id', name='user_university_course_uc'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'university_id': self.university_id,
            'course_id': self.course_id,
            'date_added': self.date_added.isoformat(),
            'university_name': self.university.name if self.university else None,
            'course_name': self.course.name if self.course else None
        }