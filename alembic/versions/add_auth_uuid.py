"""add auth_uuid to users

Revision ID: add_auth_uuid
Revises: 
Create Date: 2024-06-02 02:51:39.744478

"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = 'add_auth_uuid'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add auth_uuid column with default UUID
    op.add_column('users', sa.Column('auth_uuid', sa.String(36), nullable=True))
    
    # Update existing rows with new UUIDs
    connection = op.get_bind()
    connection.execute("UPDATE users SET auth_uuid = gen_random_uuid()::text WHERE auth_uuid IS NULL")
    
    # Make the column not nullable
    op.alter_column('users', 'auth_uuid', nullable=False)

def downgrade():
    op.drop_column('users', 'auth_uuid') 