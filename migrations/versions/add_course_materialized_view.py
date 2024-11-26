"""add_course_materialized_view

Revision ID: 44f225073899
Revises: 44f225073898
Create Date: 2024-11-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '44f225073899'
down_revision = '44f225073898'
branch_labels = None
depends_on = None

def upgrade():
    # Create materialized view for courses with their universities
    op.execute("""
        CREATE MATERIALIZED VIEW course_university_view AS
        SELECT DISTINCT
            c.id as course_id,
            c.course_name,
            c.code,
            u.program_type,
            u.university_name,
            u.id as university_id
        FROM course c
        JOIN course_requirement cr ON c.id = cr.course_id
        JOIN university u ON u.id = cr.university_id
        ORDER BY c.course_name;
        
        CREATE UNIQUE INDEX idx_course_university_view 
        ON course_university_view (course_id, university_id);
    """)

def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS course_university_view;")