import dropbox
import os
import configparser
import logging
import sys
from datetime import datetime

# Load configuration from config.ini file
config = configparser.ConfigParser()
config.read('../config.ini')

customer = config['CUSTOMER']['customer_name']
configCustomer = configparser.ConfigParser()
configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

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

class DropboxManager:
    def __init__(self, config_file):
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        customer = self.config['CUSTOMER']['customer_name']
        configCustomer = configparser.ConfigParser()
        configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)  # Go up one directory

        '''
        
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

        logger = logging.getLogger('DropboxUploader')  

        # --------------------------------LOCAL LOGGING SETUP--------------------------------
        local_log_file_path = os.path.join(project_dir, 'Dropbox Uploader', config['LOGGING_DropboxUploader']['log_file'])

        # Create a file handler for the PDFToHtmlConverter logs
        file_specific_handler = logging.handlers.RotatingFileHandler(local_log_file_path, maxBytes=int(config['LOGGING_DropboxUploader']['max_bytes']), backupCount=int(config['LOGGING_DropboxUploader']['backup_count']))
        file_specific_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_specific_handler.setLevel(config['LOGGING_DropboxUploader']['log_level']) 

        logger.addHandler(file_specific_handler)
        '''
                
        # Initialize Dropbox client
        access_token = self.config['CUSTOMER']['ACCESS_TOKEN']
        self.dbx = dropbox.Dropbox(access_token)
    
    def upload_to_dropbox(self, local_file_path, dropbox_path):
        try:
            with open(local_file_path, 'rb') as file:
                self.dbx.files_upload(file.read(), dropbox_path, mode=dropbox.files.WriteMode("overwrite"))
            logging.info(f'File uploaded successfully: {dropbox_path}')
        except Exception as e:
            print(f'Error: {e}')
            logging.error(f'Error uploading file: {e}')
            sys.exit(1)

if __name__ == '__main__':
    logger = init_logging('LOGGING_DropboxUploader', 'Dropbox Uploader')
    # Initialize DropboxManager with the path to config file
    config_file = '../config.ini'
    dropbox_manager = DropboxManager(config_file)
    config = configparser.ConfigParser()
    config.read('../config.ini')
    
    customer = config['CUSTOMER']['customer_name']
    configCustomer = configparser.ConfigParser()
    configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')

    # Define paths
    local_file_path = os.path.join(f"""{configCustomer[f"{customer}"]['local_folder_path']}""", 'Folder Storage/EpicDesktop/Clinical References Root.zip')
    zip_name = 'Clinical References Root'
    
    now = datetime.now()
    # Format the date
    formatted_date = now.strftime('%B_%d_%y')
    if ("Limited" in customer):
        zip_name += "_LIMITED_" + formatted_date + ".zip"
    if ("Full" in customer):
        zip_name += "_FULL_" + formatted_date + ".zip"
    print(f'zip name: {zip_name}')
    dropbox_folder_path = f"""{configCustomer[f"{customer}"]['dropbox_folder_path']}"""
    logging.debug(f'local file path: {local_file_path}')
    print(f'local file path: {local_file_path}')
    dropbox_path = dropbox_folder_path + '/' + os.path.basename(zip_name)
    
    # Upload the file
    dropbox_manager.upload_to_dropbox(local_file_path, dropbox_path)
