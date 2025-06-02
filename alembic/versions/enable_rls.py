"""enable rls

Revision ID: enable_rls
Revises: add_missing_columns
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'enable_rls'
down_revision = 'add_missing_columns'
branch_labels = None
depends_on = None

def upgrade():
    # Enable RLS on all tables
    op.execute('ALTER TABLE users ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE files ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE file_shares ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE file_versions ENABLE ROW LEVEL SECURITY')

    # Create policies for users table
    op.execute('''
        CREATE POLICY "Users can view their own data"
        ON users FOR SELECT
        USING (auth.uid() = id);
    ''')
    op.execute('''
        CREATE POLICY "Users can update their own data"
        ON users FOR UPDATE
        USING (auth.uid() = id);
    ''')

    # Create policies for files table
    op.execute('''
        CREATE POLICY "Users can view their own files"
        ON files FOR SELECT
        USING (auth.uid() = owner_id);
    ''')
    op.execute('''
        CREATE POLICY "Users can insert their own files"
        ON files FOR INSERT
        WITH CHECK (auth.uid() = owner_id);
    ''')
    op.execute('''
        CREATE POLICY "Users can update their own files"
        ON files FOR UPDATE
        USING (auth.uid() = owner_id);
    ''')
    op.execute('''
        CREATE POLICY "Users can delete their own files"
        ON files FOR DELETE
        USING (auth.uid() = owner_id);
    ''')

    # Create policies for file_shares table
    op.execute('''
        CREATE POLICY "Users can view their shared files"
        ON file_shares FOR SELECT
        USING (auth.uid() = shared_with_id OR 
               auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')
    op.execute('''
        CREATE POLICY "Users can share their own files"
        ON file_shares FOR INSERT
        WITH CHECK (auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')
    op.execute('''
        CREATE POLICY "Users can update their own shares"
        ON file_shares FOR UPDATE
        USING (auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')
    op.execute('''
        CREATE POLICY "Users can delete their own shares"
        ON file_shares FOR DELETE
        USING (auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')

    # Create policies for file_versions table
    op.execute('''
        CREATE POLICY "Users can view versions of their files"
        ON file_versions FOR SELECT
        USING (auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')
    op.execute('''
        CREATE POLICY "Users can create versions of their files"
        ON file_versions FOR INSERT
        WITH CHECK (auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')
    op.execute('''
        CREATE POLICY "Users can update versions of their files"
        ON file_versions FOR UPDATE
        USING (auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')
    op.execute('''
        CREATE POLICY "Users can delete versions of their files"
        ON file_versions FOR DELETE
        USING (auth.uid() IN (SELECT owner_id FROM files WHERE id = file_id));
    ''')

def downgrade():
    # Drop all policies
    op.execute('DROP POLICY IF EXISTS "Users can view their own data" ON users')
    op.execute('DROP POLICY IF EXISTS "Users can update their own data" ON users')
    
    op.execute('DROP POLICY IF EXISTS "Users can view their own files" ON files')
    op.execute('DROP POLICY IF EXISTS "Users can insert their own files" ON files')
    op.execute('DROP POLICY IF EXISTS "Users can update their own files" ON files')
    op.execute('DROP POLICY IF EXISTS "Users can delete their own files" ON files')
    
    op.execute('DROP POLICY IF EXISTS "Users can view their shared files" ON file_shares')
    op.execute('DROP POLICY IF EXISTS "Users can share their own files" ON file_shares')
    op.execute('DROP POLICY IF EXISTS "Users can update their own shares" ON file_shares')
    op.execute('DROP POLICY IF EXISTS "Users can delete their own shares" ON file_shares')
    
    op.execute('DROP POLICY IF EXISTS "Users can view versions of their files" ON file_versions')
    op.execute('DROP POLICY IF EXISTS "Users can create versions of their files" ON file_versions')
    op.execute('DROP POLICY IF EXISTS "Users can update versions of their files" ON file_versions')
    op.execute('DROP POLICY IF EXISTS "Users can delete versions of their files" ON file_versions')

    # Disable RLS
    op.execute('ALTER TABLE users DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE files DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE file_shares DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE file_versions DISABLE ROW LEVEL SECURITY') 