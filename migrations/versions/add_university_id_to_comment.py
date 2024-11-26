"""add university id to comment

Revision ID: 44f225073902
Revises: 44f225073901
Create Date: 2024-11-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '44f225073902'
down_revision = '44f225073901'  
branch_labels = None
depends_on = None

def upgrade():
    # Add university_id column to comment table
    op.add_column('comment', sa.Column('university_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_comment_university_id', 
        'comment', 'university', 
        ['university_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade():
    op.drop_constraint('fk_comment_university_id', 'comment', type_='foreignkey')
    op.drop_column('comment', 'university_id') 