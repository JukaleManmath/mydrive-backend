"""add missing columns

Revision ID: add_missing_columns
Revises: add_updated_at
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_missing_columns'
down_revision = 'add_updated_at'
branch_labels = None
depends_on = None

def upgrade():
    # Add share_date to file_shares
    op.add_column('file_shares', sa.Column('share_date', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE file_shares SET share_date = CURRENT_TIMESTAMP")
    op.alter_column('file_shares', 'share_date', nullable=False)

    # Add created_at to files
    op.add_column('files', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE files SET created_at = upload_date")
    op.alter_column('files', 'created_at', nullable=False)

    # Add updated_at to files
    op.add_column('files', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE files SET updated_at = upload_date")
    op.alter_column('files', 'updated_at', nullable=False)

def downgrade():
    op.drop_column('file_shares', 'share_date')
    op.drop_column('files', 'created_at')
    op.drop_column('files', 'updated_at') 