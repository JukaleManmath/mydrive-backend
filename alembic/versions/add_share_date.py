"""add share_date column

Revision ID: add_share_date
Revises: initial_migration
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_share_date'
down_revision = 'initial_migration'
branch_labels = None
depends_on = None

def upgrade():
    # Add share_date column with default value
    op.add_column('file_shares', sa.Column('share_date', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Make the column not nullable after setting default values
    op.alter_column('file_shares', 'share_date',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=None)

def downgrade():
    op.drop_column('file_shares', 'share_date') 