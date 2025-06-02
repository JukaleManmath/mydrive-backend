"""add missing columns

Revision ID: add_missing_columns
Revises: enable_rls
Create Date: 2024-03-19 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_missing_columns'
down_revision = 'enable_rls'
branch_labels = None
depends_on = None

def upgrade():
    # Add share_date to file_shares table
    op.add_column('file_shares', sa.Column('share_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    
    # Add created_at and updated_at to files table
    op.add_column('files', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('files', sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'), nullable=True))

def downgrade():
    # Remove columns in reverse order
    op.drop_column('files', 'updated_at')
    op.drop_column('files', 'created_at')
    op.drop_column('file_shares', 'share_date') 