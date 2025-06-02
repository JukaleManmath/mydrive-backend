"""add created_by to file_versions

Revision ID: add_created_by_to_versions
Revises: 
Create Date: 2024-06-02 02:59:51.656295

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_created_by_to_versions'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add created_by column
    op.add_column('file_versions', sa.Column('created_by', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_file_versions_created_by_users',
        'file_versions', 'users',
        ['created_by'], ['id']
    )

def downgrade():
    # Remove foreign key constraint
    op.drop_constraint('fk_file_versions_created_by_users', 'file_versions', type_='foreignkey')
    
    # Remove created_by column
    op.drop_column('file_versions', 'created_by') 