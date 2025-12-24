#!/usr/bin/env python
"""
Smart migration script that checks if tables/columns exist before applying migrations.
If they exist, fake-apply. If not, actually run the migration.
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def table_exists(table_name):
    """Check if a table exists in the database"""
    cursor = connection.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, [table_name])
    return cursor.fetchone()[0]

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    cursor = connection.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s 
            AND column_name = %s
        );
    """, [table_name, column_name])
    return cursor.fetchone()[0]

def migration_applied(app_name, migration_name):
    """Check if a migration is already applied"""
    cursor = connection.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM django_migrations 
            WHERE app = %s AND name = %s
        );
    """, [app_name, migration_name])
    return cursor.fetchone()[0]

# Migration checks: (migration_name, expected_tables_list, expected_columns_dict)
MIGRATION_CHECKS = {
    '0011_exam_studentanswer_studentexam_topic_and_more': (
        ['api_exam', 'api_studentexam', 'api_studentanswer', 'api_topic'],
        {}
    ),
    '0013_club': (
        ['api_club'],
        {}
    ),
    '0014_biodata_club': (
        [],
        {'api_biodata': ['club_id']}
    ),
    '0015_remove_biodata_club_student_club': (
        [],
        {'api_student': ['club_id']}  # Check if student.club_id exists
    ),
}

def check_migration_should_fake(migration_name, expected_tables, expected_columns):
    """Check if migration should be fake-applied based on existing tables/columns"""
    # Check tables
    for table in expected_tables:
        if not table_exists(table):
            return False, f"Missing table: {table}"
    
    # Check columns
    for table, columns in expected_columns.items():
        if not table_exists(table):
            return False, f"Table {table} doesn't exist"
        for column in columns:
            if not column_exists(table, column):
                return False, f"Missing column: {table}.{column}"
    
    return True, "All checks passed"

def smart_migrate():
    """Apply migrations intelligently"""
    print("=== Smart Migration Script ===\n")
    
    # Process migrations in order
    migrations_to_check = [
        '0011_exam_studentanswer_studentexam_topic_and_more',
        '0013_club',
        '0014_biodata_club',
        '0015_remove_biodata_club_student_club',
    ]
    
    for migration_name in migrations_to_check:
        print(f"\nChecking migration: {migration_name}")
        
        if migration_applied('api', migration_name):
            print(f"  ✓ Already applied")
            continue
        
        if migration_name not in MIGRATION_CHECKS:
            # Unknown migration, apply normally
            print(f"  → Running migration (not in checks)...")
            call_command('migrate', 'api', migration_name, fake=False)
            print(f"  ✓ Migration applied")
            continue
        
        expected_tables, expected_columns = MIGRATION_CHECKS[migration_name]
        should_fake, reason = check_migration_should_fake(migration_name, expected_tables, expected_columns)
        
        if should_fake:
            print(f"  ✓ Checks passed: {reason}")
            print(f"  → Fake-applying migration...")
            call_command('migrate', 'api', migration_name, fake=True)
            print(f"  ✓ Fake-applied successfully")
        else:
            print(f"  ✗ {reason}")
            print(f"  → Running migration...")
            try:
                call_command('migrate', 'api', migration_name, fake=False)
                print(f"  ✓ Migration applied successfully")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                # If it fails and the column/table already exists, try fake
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    print(f"  → Retrying with fake (resource already exists)...")
                    call_command('migrate', 'api', migration_name, fake=True)
                    print(f"  ✓ Fake-applied successfully")
    
    # Now apply all remaining migrations normally
    print(f"\n=== Applying remaining migrations ===")
    
    # Special handling for migration 0017 which might fail due to unique constraint
    if not migration_applied('api', '0017_add_readable_id_to_student'):
        print("\nHandling migration 0017 (readable_id for student)...")
        try:
            call_command('migrate', 'api', '0017', verbosity=1)
            print("✓ Migration 0017 applied successfully")
        except Exception as e:
            error_str = str(e)
            if 'unique' in error_str.lower() or 'duplicate' in error_str.lower():
                print(f"  ⚠ Unique constraint error: {error_str}")
                print("  → Field exists but has duplicate values. Populating unique values...")
                
                # Add field without unique constraint first
                cursor = connection.cursor()
                if not column_exists('api_student', 'readable_id'):
                    # Add column without unique constraint
                    cursor.execute("""
                        ALTER TABLE api_student 
                        ADD COLUMN readable_id VARCHAR(20);
                    """)
                    print("  ✓ Added readable_id column (non-unique)")
                
                # Populate unique values for existing students using row number
                cursor.execute("""
                    WITH numbered AS (
                        SELECT id, 'STU-' || LPAD(ROW_NUMBER() OVER (ORDER BY id)::text, 6, '0') as new_readable_id
                        FROM api_student
                        WHERE readable_id IS NULL OR readable_id = ''
                    )
                    UPDATE api_student s
                    SET readable_id = n.new_readable_id
                    FROM numbered n
                    WHERE s.id = n.id;
                """)
                print(f"  ✓ Populated readable_id for existing students")
                
                # Now add unique constraint
                cursor.execute("""
                    ALTER TABLE api_student 
                    ALTER COLUMN readable_id SET NOT NULL;
                    CREATE UNIQUE INDEX api_student_readable_id_key ON api_student(readable_id);
                """)
                print("  ✓ Added unique constraint")
                
                # Mark migration as applied
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied)
                    VALUES ('api', '0017_add_readable_id_to_student', NOW())
                    ON CONFLICT DO NOTHING;
                """)
                print("  ✓ Marked migration 0017 as applied")
    
    # Apply remaining migrations
    call_command('migrate', verbosity=1)
    print("\n✓ All migrations completed!")

if __name__ == '__main__':
    smart_migrate()