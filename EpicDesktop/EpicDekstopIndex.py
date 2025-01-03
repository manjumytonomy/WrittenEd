import os
import configparser
import zipfile
from lxml import html
from datetime import datetime
import logging
import sys
import shutil
from logging.handlers import RotatingFileHandler

'''
This code generates the EpicDesktopIndex after the PDFs have been converted to HTML and the tags have been inserted.
It does this recursively and can handle subdirectories as well. It then zips up the CSS files, HTML files, and the EpicDesktopIndex.html file all into 
one deliverable zip.
'''

config = configparser.ConfigParser()
config.read('../config.ini')


customer = config['CUSTOMER']['customer_name']
configCustomer = configparser.ConfigParser()
configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)  # Go up one directory

def init_logging(log_config, dir_name):
    # --------------------------------GLOBAL LOGGING SETUP--------------------------------
    log_file = os.path.join(project_dir, config['LOGGING']['log_file'])

    # Get the root logger -- this part makes sure that all logs are directed to the same file 
    root_logger = logging.getLogger()

    # Clear existing handlers if they exist
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Set up the file handler with rotation
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=int(config['LOGGING']['max_bytes']), backupCount=int(config['LOGGING']['backup_count']))
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    handler.setLevel(config['LOGGING']['log_level'])  # Set handler log level dynamically

    # Set the root logger level dynamically based on config
    root_logger.setLevel(logging.DEBUG)

    # Add the handler to the logger
    root_logger.addHandler(handler)

    logger = logging.getLogger(dir_name)  

    # --------------------------------LOCAL LOGGING SETUP--------------------------------
    local_log_file_path = os.path.join(project_dir, dir_name, config[log_config]['log_file'])

    # Create a file handler for the PDFToHtmlConverter logs
    file_specific_handler = logging.handlers.RotatingFileHandler(local_log_file_path, maxBytes=int(config[log_config]['max_bytes']), backupCount=int(config[log_config]['backup_count']))
    file_specific_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    file_specific_handler.setLevel(config[log_config]['log_level']) 

    logger.addHandler(file_specific_handler)

    return logger

class EpicDesktopIndex:
    def __init__(self, index_name, root_folder):
        self.index_name = index_name
        self.root_folder = root_folder
        self.TOC_html = ''
        self.files_to_zip = []

    # GENERATES THE TABLE OF CONTENTS ON THE HTML PAGE
    def generate_TOC(self):
        try:
            self.TOC_html += f'<html><head><meta charset="UTF-8"><title>{self.index_name}</title><script type="text/javascript" src="EpicVendorCommunication.js"></script></head><body>'
            self.TOC_html += f'<h1>{self.index_name}</h1>'
            self._generate_TOC_recursive(self.root_folder)
            self.TOC_html += '</body></html>'

            tree = html.fromstring(self.TOC_html)
            # Pretty print the HTML content while preserving the order
            pretty_html = html.tostring(tree, pretty_print=True, encoding='unicode')

            return pretty_html
        except Exception as e:
            logger.error(f'Error when generating Table of Contents: {e}')
            raise

    # THE RECURSIVE METHOD THAT GENERATES THE TABLE OF CONTENTS
    def _generate_TOC_recursive(self, directory, parent_path=''):
        self.TOC_html += '<ul>'

        for item in sorted(os.listdir(directory)):
            item_path = os.path.join(directory, item)
            logger.debug(f"item path: {item_path}")
            relative_path = os.path.relpath(item_path, self.root_folder)
            
            logger.debug(f"relative path: {relative_path}")
            
            # Skip output_images file
            if item == 'Images' and os.path.isdir(item_path):
                continue

            if os.path.isdir(item_path):
                self.TOC_html += f'<li>{relative_path}</li>'
                self._generate_TOC_recursive(item_path, f'{parent_path}{item}/')

            elif item.endswith('.html'):
                self.TOC_html += f'<li><a href="{"HTML/" + relative_path}">{os.path.basename(relative_path).replace(".html", "")}</a></li>'

        self.TOC_html += '</ul>'

    # ZIPS THE TABLE OF CONTENTS, CSS, AND THE HTML FILES ALL INTO ONE ZIP FILE
    def zip_files_and_folder(self, zip_filename):
        # Check if zip_filename already exists and delete if it does
        logger.debug(f'zip filename: {zip_filename}')

        images_dir = os.path.join(self.root_folder, 'Images')
        logo_image_reference_filename = os.path.join(
                configCustomer[f'{customer}']['local_folder_path'],
                f"EpicHtmlRequirements/{configCustomer[f'{customer}']['logo']}"
            )
        if os.path.exists(logo_image_reference_filename):
            shutil.copy(logo_image_reference_filename, os.path.join(images_dir, os.path.basename(logo_image_reference_filename)))
        else:
            logger.warning(f'Logo file does not exist: {logo_image_reference_filename}')
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_to_zip in self.files_to_zip:
                zipf.write(file_to_zip, os.path.basename(file_to_zip))
                
            for root, _, files in os.walk(self.root_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(self.root_folder))
                    zipf.write(file_path, arcname)
                    
            # Add CSS directory directly
            css_dir = os.path.join(project_dir, 'PDFToHtmlConverter', 'CSS')
            for root, _, files in os.walk(css_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, css_dir)
                    zipf.write(file_path, os.path.join('CSS', arcname))

        
        # Delete the files after zipping
        for file_to_delete in self.files_to_zip:
            os.remove(file_to_delete)

if __name__ == '__main__':
    logger = init_logging('LOGGING_EpicDesktopIndex', 'EpicDesktop')

    # Read configuration variables from config.ini
    index_name = 'EpicDesktopIndex'
    root_folder = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/HTML')
    
    logger.debug(f"index name: {index_name}")
    logger.debug(f"root folder: {root_folder}")

    try:
        index = EpicDesktopIndex(index_name, root_folder)
        TOC_html = index.generate_TOC()
        main_index_file = index_name + '.html'
        
        with open(main_index_file, 'w', encoding='utf-8') as TOC_file:
            TOC_file.write(TOC_html)
            
        index.files_to_zip.append(main_index_file)

        output_folder = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/EpicDesktop')

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        else:
            # Delete all contents of the output folder
            for root, dirs, files in os.walk(output_folder, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))
            logger.info(f"Deleted all contents of {output_folder}")

        
        # Ensure the output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        zip_filename = os.path.join(output_folder, 'Clinical References Root.zip')
        
        index.zip_files_and_folder(zip_filename)
    except Exception as e:
        logger.error(f'Error when generating Epic Desktop Index: {e}')
        sys.exit(1)
