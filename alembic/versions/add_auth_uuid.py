"""add auth uuid

Revision ID: add_auth_uuid
Revises: enable_rls
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'add_auth_uuid'
down_revision = 'enable_rls'
branch_labels = None
depends_on = None

def upgrade():
    # Add auth_uuid column to users table
    op.add_column('users', sa.Column('auth_uuid', UUID(as_uuid=True), nullable=True))
    
    # Create a function to get the auth.uid()
    op.execute("""
        CREATE OR REPLACE FUNCTION get_auth_uid()
        RETURNS uuid AS $$
        BEGIN
            RETURN auth.uid();
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

def downgrade():
    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS get_auth_uid()")
    
    # Drop the column
    op.drop_column('users', 'auth_uuid') 