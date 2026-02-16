import os
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = "Remove duplicate or invalid migration entries from the `django_migrations` table"

    def handle(self, *args, **kwargs):
        # Step 1: Fetch all migration entries from the database
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, app, name FROM django_migrations")
            migrations = cursor.fetchall()

        # Organize migrations by app and prefix (e.g., "008", "009")
        duplicates = defaultdict(list)
        for migration_id, app, name in migrations:
            prefix = name.split("_")[0]  # Extract the prefix (e.g., "008")
            duplicates[(app, prefix)].append((migration_id, name))

        # Step 2: Validate against the migration files
        valid_migrations = {}
        for app_config in apps.get_app_configs():
            migrations_dir = os.path.join(app_config.path, "migrations")
            if os.path.isdir(migrations_dir):
                valid_migrations[app_config.label] = {
                    f[:-3] for f in os.listdir(migrations_dir) if f.endswith(".py") and f != "__init__.py"
                }

        # Step 3: Identify and remove invalid duplicates
        removed_entries = []
        for (app, prefix), entries in duplicates.items():
            if len(entries) > 1:  # Only handle duplicates
                valid_names = valid_migrations.get(app, set())
                valid_entry = next((entry for entry in entries if entry[1] in valid_names), None)

                for migration_id, name in entries:
                    if valid_entry and (migration_id, name) == valid_entry:
                        continue  # Skip the valid entry
                    # Remove the invalid entry
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM django_migrations WHERE id = %s", [migration_id])
                    removed_entries.append((app, name))

        # Step 4: Output results
        if removed_entries:
            self.stdout.write("Removed the following invalid migration entries:")
            for app, name in removed_entries:
                self.stdout.write(f"  {app}: {name}")
        else:
            self.stdout.write("No duplicate or invalid migrations found.")
