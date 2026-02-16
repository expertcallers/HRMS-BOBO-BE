import os
import shutil


# Define your Django project's base folder

# Define the destination folder where you want to copy the migrations


# Function to copy migrations folders to the specified directory
def ignore_files_and_folders(directory, contents):
    return [item for item in contents if item != 'migrations']


# Copy migrations folders to the specified directory
def remove_migrations(base_folder):
    for root, dirs, files in os.walk(base_folder):
        if 'venv' in root:
            continue
        if 'migrations' in dirs:
            migrations_folder = os.path.join(root, 'migrations')

            for iroot, idirs, ifiles in os.walk(migrations_folder):
                for ijfile in ifiles:
                    file_path = os.path.join(migrations_folder, ijfile)
                    # print(f"{file_path}")
                    if ijfile != "__init__.py" and os.path.exists(file_path):
                        os.remove(os.path.join(migrations_folder, ijfile))


# Copy migrations folders to the specified directory
remove_migrations(os.getcwd())
