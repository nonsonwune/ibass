from ..extensions import db
from .base import BaseModel
from sqlalchemy.dialects.postgresql import JSONB

class SpecialRequirement(BaseModel):
    __tablename__ = 'special_requirement'
    
    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    requirements = db.Column(JSONB)  # Store requirements as JSON
    special_notes = db.Column(JSONB)  # Store special notes as JSON
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.now(), onupdate=db.func.now())
    
    # The backref is now defined in the University model
    
    def __repr__(self):
        return f"<SpecialRequirement for University {self.university_id}>"
