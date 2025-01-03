import os
import pandas as pd
import re
import configparser
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
'''
This code checks every single HTML file and determines if the rules of the tags are violated according to EPIC's specifications. Will
probably change this code to be more function oriented where we can pass in the content of an HTML page instead and have that checked, instead
of running through every single file again and having it check in post.
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
    
class TagValidator:
    def setUp(self):
        logger.info("RUNNING EPIC TAG VALIDATOR")
        self.errorCount = 0
        self.log_file = os.path.join(project_dir, config['LOGGING']['log_file'])
        self.html_folder = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/HTML')   
    
    def check_for_illegal_chars(self, text, chars, tab_str, tag_type):
            illegal_chars_found = []
            if tag_type == 'title':
                for char in chars:
                    if char in text:
                        illegal_chars_found.append(char)
                if tab_str in text:
                    illegal_chars_found.append(tab_str)
            return illegal_chars_found

    def validate_tags(self):
        for root, _, files in os.walk(self.html_folder):
            for file in files:
                if file.endswith(".html"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    '''
                    FOR DOCTYPE, XML, UTF-8 ENCODING, JAVASCRIPT, AND CSS TAGS
                    '''

                    #DOCTYPE TAG
                    doctype_tag = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'''
                    if doctype_tag not in content:
                        logger.error(f"DOCTYPE Tag does not exist in file {file_path}\n")
                        self.errorCount += 1

                    #XML TAG
                    xml_tag = '''<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">'''
                    if xml_tag not in content:
                        logger.error(f"XML Tag does not exist in file {file_path}\n")
                        self.errorCount += 1

                    #UTF-8 ENCODING TAG
                    utf_encoding = '''<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'''
                    if utf_encoding not in content:
                        logger.error(f"UTF-8 ENCODING Tag does not exist in file {file_path}\n")
                        self.errorCount += 1

                    #JAVASCRIPT TAG
                    js_tag = '''<script type="text/javascript" src="..\..\EpicVendorCommunication.js"></script>'''
                    if js_tag not in content:
                        logger.error(f"JAVASCRIPT Tag does not exist in file {file_path}\n")
                        self.errorCount += 1

                    #CSS TAG
                    css_tag = '''<link rel="stylesheet" type="text/css" href="..\..\CSS\WEMytonomy.css" />'''
                    if css_tag not in content:
                        logger.error(f"CSS Tag does not exist in file {file_path}\n")
                        self.errorCount += 1

                    '''
                    FOR TITLE TAG
                    '''
                    title_pattern = r'<title>([^<]*)</title>'
                    title_tag = re.search(title_pattern, content)
                    if title_tag:
                        title_content = title_tag.group(1)
                        #print(f'titletag: {title_content}')
                        chars_to_detect = "[],|^"
                        tab = '<tab>'
                        #illegal_chars = self.check_for_illegal_chars(title_content, chars_to_detect, tab, 'title')
                        #print(illegal_chars)   
                        if len(title_content) == 0:
                            logger.error(f"Empty title tag in file {file_path}\n")
                            self.errorCount += 1     
                        else: 
                            illegal_chars = self.check_for_illegal_chars(title_content, chars_to_detect, tab, 'title')           
                            if illegal_chars:
                                logger.error(f"Detected illegal character(s) in title tag in file {file_path}: {illegal_chars}\n")
                                self.errorCount += 1
                    else:
                        logger.error(f"Title tag does not exist in file {file_path}\n")
                        self.errorCount += 1

                    if title_content.encode('ascii'):
                         logger.error(f"Title tag contains non ASCII character {file_path}\n")
                         self.errorCount += 1
                    
                    '''
                    FOR UNIQUE NAME TAG
                    '''
                    unique_name_pattern = r'<meta\s+name="Unique"\s+content="([^"]*)"\s*/?>'
                    matches = re.findall(unique_name_pattern, content)
                    if not matches:
                        logger.error(f"Unique name tag does not exist in file {file_path}\n")
                        self.errorCount += 1
                    #print(matches)
                    if len(matches) > 1:
                        print("detected duplicate")
                        logger.error(f"Duplicate unique name tags found in file {file_path}\n")
                        self.errorCount += 1
                    for unique_name in matches:
                        if len(unique_name) > 192 or not re.match(r'^[a-zA-Z0-9\-_.]+$', unique_name):
                            logger.error(f"Invalid unique name tag in file {file_path}: {unique_name}\n")
                            self.errorCount += 1
                        elif len(unique_name) == 0:
                            logger.error(f"Empty unique name tag in file {file_path}: {unique_name}\n")
                            errorCount += 1

                    '''
                    FOR KEYWORD TAG
                    '''
                    total_keywords = 0
                    keywords_pattern = r'<meta\s+name="Keywords"\s+content="([^"]*)"\s*/?>'
                    matches = re.findall(keywords_pattern, content)
                    if not matches:
                        logger.error(f"Keyword Tag does not exist in file {file_path}\n")
                        self.errorCount += 1
                    else:   
                        for match in matches:
                            if len(match.strip()) == 0:
                                logger.error(f"Empty Keyword Tag in file {file_path}\n")
                                self.errorCount += 1
                            else:
                                keywords = match.split(',')
                                for word in keywords:
                                    if len(word) > 184:
                                        logger.error(f"Keyword longer than 184 characters in file {file_path}: {len(word)}\n")
                                        self.errorCount += 1
                                    total_keywords += 1
                        
                    if total_keywords > 500:
                        logger.error(f"More than 500 keywords detected in file {file_path}\n")
                        self.errorCount += 1

                    '''
                    FOR LANGUAGE TAG 
                    '''
                    language_pattern = r'<meta\s+name="Language"\s+content="([^"]*)"\s*/?>'
                    matches = re.findall(language_pattern, content, re.IGNORECASE)
                    #logging.debug(f'Detected {len(matches)} for Language Tag')
                    if not matches:
                        logger.error(f"Language Tag does not exist in file {file_path}\n")
                        self.errorCount += 1
                    else:
                        if len(matches) == 0:
                            logger.error(f'Empty Language Tag in file {file_path}.')
                            self.errorCount += 1
                        elif len(matches) > 1:
                            logger.error(f'Detected more than 1 Language Tag in file {file_path}.')
                            self.errorCount += 1

                    '''
                    FOR SOURCE TAG
                    '''
                    source_pattern = r'<meta\s+name="Source"\s+content="([^"]*)"\s*/?>'
                    matches = re.findall(source_pattern, content, re.IGNORECASE)
                    if not matches:
                        logger.warning(f"Optional Source Tag does not exist in file {file_path}\n")
                        self.errorCount += 1
                    else:
                        if len(matches) == 0:
                            logger.error(f'Empty Source Tag in file {file_path}.')
                            self.errorCount += 1
                        elif len(matches) > 1:
                            logger.error(f'Detected more than 1 Source Tag in file {file_path}')

                    '''
                    FOR DOCUMENT TYPE TAG
                    '''
                    document_type_tag = r'<meta\s+name="DocumentType"\s+content="([^"]*)"\s*/?>'
                    matches = re.findall(document_type_tag, content)
                    if not matches:
                        logger.warning(f"Optional Document Type Tag does not exist in file {file_path}\n")
                        self.errorCount += 1
                    else:
                        for match in matches:
                            if len(match) == 0:
                                logger.error(f'Empty Document Type Tag in file {file_path}.')
                                self.errorCount += 1
                            elif match != "Patient Education" and match != "Physician Reference":
                                logger.error(f"Detected unknown Document Type Tag in file {file_path}")
                        
                    '''
                    FOR AGE TAG
                    '''
                    age_tag = r'<meta\s+name="Age"\s+content="([^"]*)"\s*/?>'
                    matches = re.findall(age_tag, content, re.IGNORECASE)
                    if not matches:
                        logger.warning(f"Optional Age Tag does not exist in file {file_path}\n")
                        self.errorCount += 1
                    else:
                        if len(matches) == 0:
                                logger.error(f'Empty Age Tag in file {file_path}.')
                                self.errorCount += 1
                        if len(matches) > 1:
                            logger.error(f'More than 1 Age Tag in file {file_path}')
                            self.errorCount += 1

                    '''
                    FOR GENDER TAG
                    '''
                    gender_tag = r'<meta\s+name="Gender"\s+content="([^"]*)"\s*/?>'
                    matches = re.findall(gender_tag, content)
                    if not matches:
                        logger.warning(f"Optional Gender Tag does not exist in file {file_path}\n")
                        self.errorCount += 1
                    else:
                        if len(matches) == 0:
                            logger.error(f'Empty Gender Tag in file {file_path}.')
                            self.errorCount += 1
                        elif len(matches) > 1:
                            logger.error(f'More than 1 Gender Tag in file {file_path}')
                            self.errorCount += 1
                        for match in matches:
                            if match != "female" and match != "male" and match != "Both":
                                logger.error(f'Invalid Gender Tag detected in {file_path}')
                                self.errorCount += 1
                            if match.lower() == "both" and match != "Both":
                                logger.error(f"Uncapitalized 'b' in gender tag for 'Both' in {file_path}")
                                self.errorCount += 1
    
    

#    with open('meta-tag-validation-errors.log', 'w') as f:

if __name__ == '__main__':
    logger = init_logging('LOGGING_TagValidator', 'Tag Validator')
    validator = TagValidator()
    validator.setUp()  
    validator.validate_tags()
