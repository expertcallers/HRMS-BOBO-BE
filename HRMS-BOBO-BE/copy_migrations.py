import os
import shutil

# Define your Django project's base folder
base_project_folder = os.getcwd()

# Define the destination folder where you want to copy the migrations
destination_folder = os.path.expanduser('~') + "/migrations/" + os.path.basename(base_project_folder)


# Function to copy migrations folders to the specified directory
def ignore_files_and_folders(directory, contents):
    return [item for item in contents if item != 'migrations']


# Copy migrations folders to the specified directory
def copy_migrations_to_destination(base_folder, destination):
    for root, dirs, files in os.walk(base_folder):
        if 'venv' in root:
            continue
        if 'migrations' in dirs:
            migrations_folder = os.path.join(root, 'migrations')
            dest_folder = os.path.join(destination, os.path.relpath(root, base_folder))
            dest_migrations_folder = os.path.join(dest_folder, 'migrations')
            if not os.path.exists(dest_migrations_folder):
                os.makedirs(dest_migrations_folder)
            # print(os.listdir(migrations_folder))
            for file_name in os.listdir(migrations_folder):
                source_file_path = os.path.join(migrations_folder, file_name)
                destination_file_path = os.path.join(dest_migrations_folder, file_name)
                if os.path.isfile(source_file_path):  # Check if it's a file
                    shutil.copyfile(source_file_path, destination_file_path)


# Copy migrations folders to the specified directory
copy_migrations_to_destination(base_project_folder, destination_folder)
