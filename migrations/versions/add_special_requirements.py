"""Add special requirements table

Revision ID: 44f225073901
Revises: 44f225073900
Create Date: 2024-11-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '44f225073901'
down_revision = '44f225073900'
branch_labels = None
depends_on = None

def upgrade():
    # Create special_requirement table
    op.create_table('special_requirement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('university_id', sa.Integer(), nullable=False),
        sa.Column('requirements', JSONB(), nullable=True),
        sa.Column('special_notes', JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['university_id'], ['university.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Create index on university_id for faster lookups
    op.create_index(op.f('ix_special_requirement_university_id'), 'special_requirement', ['university_id'], unique=False)

def downgrade():
    # Drop index first
    op.drop_index(op.f('ix_special_requirement_university_id'), table_name='special_requirement')
    # Then drop table
    op.drop_table('special_requirement')
