import dropbox
import os
import configparser
import logging
import zipfile
import sys
import shutil
from logging.handlers import RotatingFileHandler

'''
This program downloads the zip file from dropbox shared link, unzips it, and places the contents in a folder called DownloadedPDFs in FolderStorage
'''

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

class DropboxDownloader:
    '''
    Class to handle downloading and extracting files from a shared Dropbox link.
    '''

    def __init__(self):
        '''
        Initialize the DropboxDownloader with access token and shared link from the config file.
        Set up local folder path for storing downloaded files.
        '''
        self.access_token = config['CUSTOMER']['ACCESS_TOKEN']
        self.shared_link = configCustomer[f"{customer}"]['shared_link']
        self.local_folder_path = os.path.join(f"""{configCustomer[f"{customer}"]['local_folder_path']}""", 'Folder Storage')
        if not os.path.exists(self.local_folder_path):
            os.makedirs(self.local_folder_path)
            print(f"Directory '{self.local_folder_path}' created.")
        else:
            print(f"Directory '{self.local_folder_path}' already exists.")
        try:
            self.dbx = dropbox.Dropbox(self.access_token)
        except Exception as e:
            logger.error (f"An error occured while initiating the Dropbox connector: {e}")

    def list_folder(self, shared_link_obj, folder_path='', local_folder=None):
        '''
        List the contents of the shared Dropbox folder and download the first file found.
        '''
        if local_folder is None:
            local_folder = self.local_folder_path

        try:
            folder_entries = self.dbx.files_list_folder(folder_path, shared_link=shared_link_obj).entries
        except Exception as e:
            logger.error(f"An error occurred while accessing entries: {e}")
            raise

        if len(folder_entries) == 0:
            logger.warning("No files found in the shared folder.")
            return None

        entry = folder_entries[0]  # Get the first entry
        entry_name = str(entry.name).replace("?", "")
        logger.debug(f"File to download: {entry_name}")

        local_file_path = os.path.join(local_folder, entry_name)
        logger.debug(f'local file path: {local_file_path}')

        try:
            with open(local_file_path, 'wb') as f:
                md, res = self.dbx.sharing_get_shared_link_file(url=self.shared_link, path=f'{folder_path}/{entry.name}')

                f.write(res.content)
        except Exception as e:
            logger.error(f"Failed to download file {entry_name}: {e}")
            raise

        logger.info(f"File downloaded: {entry_name}")

        return local_file_path

    def unzip_file(self, zip_file_path, extract_folder):
        '''
        Unzip a zip file to a specified folder.
        '''
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                extract_path = os.path.join(extract_folder, 'DownloadedPDFs')
                os.makedirs(extract_path, exist_ok=True)
                logger.info("Made DownloadedPDFs directory")
                zip_ref.extractall(extract_path)
                logger.info(f"File {zip_file_path} extracted to {extract_path}")
        except Exception as e:
            logger.error(f"Failed to extract file {zip_file_path}: {e}")
            raise

        return extract_path

    def delete_existing_downloaded_pdfs(self):
        '''
        Delete the existing 'DownloadedPDFs' folder if it exists.
        '''
        downloaded_pdfs_path = os.path.join(self.local_folder_path, 'DownloadedPDFs')
        if os.path.exists(downloaded_pdfs_path):
            try:
                shutil.rmtree(downloaded_pdfs_path)
                logger.info(f"Existing DownloadedPDFs folder deleted: {downloaded_pdfs_path}")
            except Exception as e:
                logger.error(f"Failed to delete existing DownloadedPDFs folder: {e}")
                raise

    def access_shared_folder(self):
        '''
        Main method to handle the process of downloading, extracting, and renaming files from Dropbox.
        '''
        try:
            # Check and delete existing DownloadedPDFs folder if exists
            self.delete_existing_downloaded_pdfs()

            shared_link_obj = dropbox.files.SharedLink(url=self.shared_link)
            downloaded_file_path = self.list_folder(shared_link_obj)
            if downloaded_file_path:
                # Unzip the downloaded file into the DownloadedPDFs directory
                extract_folder = os.path.dirname(downloaded_file_path)
                logger.info(f'extract folder name: {extract_folder}')
                extracted_folder = self.unzip_file(downloaded_file_path, extract_folder)

                # Optionally delete the original downloaded zip file
                os.remove(downloaded_file_path)
                logger.info(f"Deleted original zip file: {downloaded_file_path}")

                downloaded_pdfs_path = os.path.join(self.local_folder_path, 'DownloadedPDFs')
                macosx_path = os.path.join(downloaded_pdfs_path, '__MACOSX')

                # Check if __MACOSX directory exists
                if os.path.exists(macosx_path) and os.path.isdir(macosx_path):
                    # Delete __MACOSX directory and its contents
                    shutil.rmtree(macosx_path)
                    logger.info(f"Deleted {macosx_path} and all its contents.")
                else:
                    logger.info("{macosx_path} does not exist or is not a directory.")

        except Exception as e:
            logger.error(f"An error occurred while accessing shared link: {e}")
            sys.exit(1)

if __name__ == "__main__":
    '''
    Instantiate the DropboxDownloader and start the process.
    '''
    logger = init_logging('LOGGING_PDFDownloader', 'PDFDownloader')

    print(f'customer: {customer}')
    print(f"""config customer local path: {configCustomer[f"{customer}"]['local_folder_path']}""")
    downloader = DropboxDownloader()
    downloader.access_shared_folder()
