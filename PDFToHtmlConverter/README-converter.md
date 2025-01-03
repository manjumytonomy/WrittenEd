# Written Education Project

This program converts PDF files to HTML files while preserving the original layout, including text, images, and structure. It traverses a directory of PDF files, converts each PDF to HTML, and maintains the same directory structure for the HTML files.

Features:
- Converts PDF files to HTML format
- Preserves the layout, including text and images
- Maintains the directory structure of the original PDF files
- Saves all extracted images in a central directory

## Run the Shell Script to Convert given PDF files to HTML

This script will update the config file with the paths you provide for the input and output directories, create a virtual environment and install required packages, and deactivate the virtual environment once completed.

 1. After opening terminal/command prompt, navigate to the location where the Written Education Project folder is   stored

 2. Run the following command to execute the shell script, ensuring that for the arguments you specify the path to where the PDF file directory and where you would like the output HTML directory to be created :

 ./run_WrittenEducationProject.sh /path_to_pdf_files /path_to_output_html_directory
