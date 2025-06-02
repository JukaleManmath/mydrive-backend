"""remove created_by from file_versions

Revision ID: remove_created_by
Revises: enable_rls
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_created_by'
down_revision = 'enable_rls'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the created_by column from file_versions table
    op.drop_column('file_versions', 'created_by')


def downgrade():
    # Add back the created_by column
    op.add_column('file_versions',
        sa.Column('created_by', sa.Integer(), nullable=True)
    ) 