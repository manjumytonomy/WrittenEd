#!/bin/bash

# Project directory path
PROJECT_DIR="$(dirname "$0")"

# Define necessary paths
REQUIREMENTS_FILE_PATH="$PROJECT_DIR/dependent_libraries.txt"

# NEW VENV ACCESS CODE
CUSTOMER_NAME=$(awk -F "=" '/\[CUSTOMER\]/ {flag=1; next} flag && /^customer_name/ {print $2; exit}' "$PROJECT_DIR/config.ini" | sed 's/^ *//; s/ *$//')

echo "CUSTOMER NAME: $CUSTOMER_NAME"

# Form the new config filename
NEW_CONFIG_FILENAME="CustomerConfigs/${CUSTOMER_NAME}_config.ini"

# Parse the config.ini file to get the venv path
VENV_BASE_PATH=$(awk -F "=" '/local_folder_path/ {print $2}' "$NEW_CONFIG_FILENAME" | sed 's/^ *//; s/ *$//')
VENV_PATH="$VENV_BASE_PATH/lib"

echo "Virtual environment path: $VENV_PATH"

# Access project directory
cd "$PROJECT_DIR" || exit

# Virtual environment creation
python3 -m venv "$VENV_PATH"

# Using virtual environment
source "$VENV_PATH/bin/activate"

# Upgrading pip
pip install --upgrade pip

# Installing requirements
pip install -r "$REQUIREMENTS_FILE_PATH"

# Deactivate virtual environment
deactivate

echo "Setup complete. Virtual environment created and dependencies installed at $VENV_PATH."
