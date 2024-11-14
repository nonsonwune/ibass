"""add university id to comment

Revision ID: add_university_id_to_comment
Revises: previous_migration_id
Create Date: 2024-11-14 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_university_id_to_comment'
down_revision = 'previous_migration_id'  # replace with your last migration id
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