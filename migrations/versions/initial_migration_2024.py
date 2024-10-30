"""initial migration

Revision ID: initial_migration_2024
Revises: None
Create Date: 2024-10-30 16:20:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'initial_migration_2024'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create university table
    op.create_table('university',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('university_name', sa.String(length=256), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('program_type', sa.String(length=50), nullable=False),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('established', sa.Integer(), nullable=True),
        sa.Column('abbrv', sa.String(length=255), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('university_name')
    )
    
    # Create indexes for university
    op.create_index('idx_university_name', 'university', ['university_name'])
    op.create_index('idx_university_program_type', 'university', ['program_type'])
    op.create_index('idx_university_state', 'university', ['state'])
    op.create_index('idx_university_search', 'university', ['search_vector'], postgresql_using='gin')

    # Create course table
    op.create_table('course',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_name', sa.String(length=256), nullable=False),
        sa.Column('university_name', sa.String(length=256), nullable=False),
        sa.Column('direct_entry_requirements', sa.Text(), nullable=True),
        sa.Column('utme_requirements', sa.Text(), nullable=True),
        sa.Column('subjects', sa.Text(), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.ForeignKeyConstraint(['university_name'], ['university.university_name']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for course
    op.create_index('idx_course_name', 'course', ['course_name'])
    op.create_index('idx_course_university', 'course', ['university_name'])
    op.create_index('idx_course_search', 'course', ['search_vector'], postgresql_using='gin')

def downgrade():
    op.drop_table('course')
    op.drop_table('university')