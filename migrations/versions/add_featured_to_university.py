"""add_featured_to_university

Revision ID: 44f225073898
Revises: 44f225073897
Create Date: 2024-11-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '44f225073898'
down_revision = '44f225073897'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('university', sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    op.drop_column('university', 'is_featured')
