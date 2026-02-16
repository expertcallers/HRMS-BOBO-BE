#!/bin/bash

# Check if an argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <mode>"
    exit 1
fi

# Set the mode from the first argument
MODE=$1

# Set the path to your virtual environment
PROJECT_PATH="/root/hrms/HRMS-BOBO-BE"
#PROJECT_PATH="/home/hk/PycharmProjects/HRMS-BOBO-BE"

VENV_PATH="$PROJECT_PATH/venv/bin/activate"  # Adjust this to your venv folder name

# Set the path to your Django project as the current directory

# Activate the virtual environment
source "$VENV_PATH"

# Change to your project directory
cd "$PROJECT_PATH" || exit 1  # Exit if the cd command fails


# Run the Django management command with the specified mode
python manage.py seed --mode="$MODE"
