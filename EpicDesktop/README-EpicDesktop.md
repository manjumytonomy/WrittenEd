# HTML Table of Contents Generator

This program processes HTML files and generates an HTML table of contents for them. The script `main.py` is executed through a shell script named `run_main.sh`.

## Setup

1. Make sure `main.py` and `run_main.sh` are in the same directory.

2. In `config.ini`:

    ```ini
    [settings]
    INDEX_NAME = your_index_name.html
    ROOT_FOLDER = /path/to/your/root_html_folder
    ```

    Replace `your_index_name.html` with the desired name for the generated index file and `/path/to/your/root_html_folder` with the path to the root folder containing your HTML files.

## Usage

1. Make the shell script executable by running the following command:

    ```sh
    chmod +x run_main.sh
    ```

2. Execute the shell script:

    ```sh
    ./run_main.sh
    ```

    This will run `main.py` with the configuration provided in `config.ini`.

3. The program will then output a zip file with your HTML index and the required files to access it locally.