"""add updated_at column

Revision ID: add_updated_at
Revises: add_share_date
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_updated_at'
down_revision = 'add_share_date'
branch_labels = None
depends_on = None

def upgrade():
    # Add updated_at column with default value
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Set initial value to current timestamp
    op.execute("UPDATE users SET updated_at = CURRENT_TIMESTAMP")
    
    # Make the column not nullable after setting default values
    op.alter_column('users', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False)

def downgrade():
    op.drop_column('users', 'updated_at') 