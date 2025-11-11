from django.db import migrations, connection


def drop_personal_email_column(apps, schema_editor):
    table_name = 'staff'
    column_name = 'personal_email'

    # Check if the column exists first
    try:
        with connection.cursor() as cursor:
            vendor = connection.vendor
            column_exists = False

            if vendor == 'postgresql':
                cursor.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                    """,
                    [table_name, column_name],
                )
                column_exists = cursor.fetchone() is not None
            elif vendor == 'mysql':
                cursor.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
                    """,
                    [table_name, column_name],
                )
                column_exists = cursor.fetchone() is not None
            else:
                # SQLite: use PRAGMA
                cursor.execute(f"PRAGMA table_info({table_name});")
                rows = cursor.fetchall()
                column_exists = any(row[1] == column_name for row in rows)

            if not column_exists:
                return

            # Attempt to drop the column
            try:
                if vendor == 'postgresql':
                    schema_editor.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name};")
                elif vendor == 'mysql':
                    schema_editor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name};")
                else:
                    # SQLite 3.35+ supports DROP COLUMN
                    try:
                        schema_editor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name};")
                    except Exception:
                        # As a fallback, silently ignore on older SQLite versions.
                        # The column being extra doesn't break Django since it's not in the model meta.
                        pass
            except Exception:
                # Do not fail deployment if dropping column fails; leave DB usable
                pass
    except Exception:
        # Any introspection failure should not block migration
        pass


def noop_reverse(apps, schema_editor):
    # No reverse operation
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0027_alter_salarygrade_grade_number'),
    ]

    operations = [
        migrations.RunPython(drop_personal_email_column, noop_reverse),
    ]
