#!/bin/bash

# Define necessary paths
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT_PATH="$SCRIPT_DIR/MytonomyPDFConverter.py"
CONFIG_FILE_PATH="$PROJECT_DIR/config.ini"

# NEW VENV ACCESS CODE
CUSTOMER_NAME=$(awk -F "=" '/\[CUSTOMER\]/ {flag=1; next} flag && /^customer_name/ {print $2; exit}' "$PROJECT_DIR/config.ini" | sed 's/^ *//; s/ *$//')

# Form the new config filename
NEW_CONFIG_FILENAME="CustomerConfigs/${CUSTOMER_NAME}_config.ini"

# Parse the config.ini file to get the venv path
VENV_BASE_PATH=$(awk -F "=" '/local_folder_path/ {print $2}' "$NEW_CONFIG_FILENAME" | sed 's/^ *//; s/ *$//')
VENV_PATH="$VENV_BASE_PATH/lib"

echo "Virtual environment path: $VENV_PATH"

# Access script directory
cd "$SCRIPT_DIR" || exit

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run the Python script and capture exit code
python3 "$PYTHON_SCRIPT_PATH"
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

# Output the exit code for visibility (optional)
echo "MytonomyPDFConverter.py.py exited with code: $EXIT_CODE"

# Exit with the same code as Python script to propagate it
exit $EXIT_CODE
