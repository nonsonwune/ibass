"""add_course_search_indexes

Revision ID: 44f225073900
Revises: 44f225073899
Create Date: 2024-11-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '44f225073900'
down_revision = '44f225073899'
branch_labels = None
depends_on = None

def upgrade():
    # Create composite index for course requirements
    op.create_index(
        'idx_course_req_composite',
        'course_requirement',
        ['course_id', 'university_id'],
        unique=False
    )
    
    # Create index for university program_type for IN clause queries
    op.create_index(
        'idx_university_program_type_hash',
        'university',
        ['program_type'],
        postgresql_using='hash'
    )

def downgrade():
    op.drop_index('idx_course_req_composite')
    op.drop_index('idx_university_program_type_hash') 