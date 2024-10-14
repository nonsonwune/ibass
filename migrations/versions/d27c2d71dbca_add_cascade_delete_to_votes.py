"""Add cascade delete to votes

Revision ID: d27c2d71dbca
Revises: 037bf9fba744
Create Date: 2024-10-14 04:22:26.695744

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d27c2d71dbca"
down_revision = "037bf9fba744"
branch_labels = None
depends_on = None


def upgrade():
    # Create a new table with the desired schema
    op.create_table(
        "new_vote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("vote_type", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["comment_id"], ["comment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Copy data from the old table to the new one
    op.execute(
        "INSERT INTO new_vote SELECT id, user_id, comment_id, vote_type, timestamp FROM vote"
    )

    # Drop the old table
    op.drop_table("vote")

    # Rename the new table to the original name
    op.rename_table("new_vote", "vote")


def downgrade():
    # Create a new table without CASCADE
    op.create_table(
        "new_vote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("vote_type", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["comment_id"], ["comment.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Copy data from the old table to the new one
    op.execute(
        "INSERT INTO new_vote SELECT id, user_id, comment_id, vote_type, timestamp FROM vote"
    )

    # Drop the old table
    op.drop_table("vote")

    # Rename the new table to the original name
    op.rename_table("new_vote", "vote")
