"""add is_deleted column

Revision ID: add_is_deleted_column
Revises: enable_rls
Create Date: 2024-03-19 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_is_deleted_column'
down_revision = 'enable_rls'
branch_labels = None
depends_on = None

def upgrade():
    # Add is_deleted column to files table with default value False
    op.add_column('files', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))

def downgrade():
    # Remove is_deleted column from files table
    op.drop_column('files', 'is_deleted') 