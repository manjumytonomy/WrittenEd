import pandas as pd
import configparser
import os
import re
from lxml import html
from datetime import datetime
import logging
import sys
from htmlprettify import process_single_html_file
from bs4 import BeautifulSoup
import shutil
import math
from logging.handlers import RotatingFileHandler

'''
This code takes tag information from the spreadsheet specified in config.ini and creates meta tags to EPIC's specifications and then inserts them into the HTMLs that were converted from the PDFs.
'''

config = configparser.ConfigParser()
config.read('../config.ini')

customer = config['CUSTOMER']['customer_name']
replaceqrcodesandshorturls = config['OPTION_FLAGS']['replaceqrcodesandshorturls']
#removed_unwanted_text_flag = config['OPTION_FLAGS']['removeunwantedtext']

configCustomer = configparser.ConfigParser()
configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')
cl_relative_path = configCustomer[f'{customer}']['cl_relative_path']

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

class MetaTagGenerator:
    def __init__(self, file, file_to_insert):
        self.file = file
        self.file_to_insert = file_to_insert
        self.result = {}
        self.used_titles = set()  # To keep track of used titles
    
    # GENERATING THE TAGS FROM THE SPREADSHEET
    def generate_tags(self):
        df = pd.read_excel(self.file)
        for index, row in df.iterrows():
            filepath = row["Filepath"].replace(".pdf", ".html").replace("'","").replace('"','').replace('&',' and ').replace(':','_').replace('’','')
            unique_name_tag = f'<meta name="Unique" content="{row["Unique Name"]}" />'
            keyword_tag = f'<meta name="Keywords" content="{row["Keyword"]}" />'
            diagnosis_code_tag = f'<meta name="Diagnosis codes" codeset="ICD-10-CM" content="{row["Diagnosis Code"]}" />'
            language_tag = f'<meta name="Language" content="{row["Language"]}" />'
            corresponding_language_tag = "" # Declaring variable to avoid naan
            
            # Check for cell if it is not empty and it is not a nan value
            if row["Corresponding Language"] and not type(row["Corresponding Language"]) == float:
                if cl_relative_path == 'True':
                    corresponding_language_tag = f'<meta name="Corresponding {row["Corresponding Language"]}" content="{"../" + row["Corresponding Language"] + "/"+row["Language Index"] }" />'
                else: 
                    corresponding_language_tag = f'<meta name="Corresponding {row["Corresponding Language"]}" content="{row["Language Index"]}" />'
            source_tag = f'<meta name="Source" content="{row["Source"]}" />'
            document_type_tag = '<meta name="DocumentType" content="Patient Education" />'
            cpt_code_tag = f"""<meta name="CPT codes" content="{row['CPT Code']}" />"""
            title = row["Title"]

            if 'Short URL' in df.columns:
                short_url = row['Short URL'] 
            else:
                short_url = ""

            if 'QR Code' in df.columns:
                qr_code = row['QR Code']
            else: 
                qr_code = ""

            #self.result[filepath] = [unique_name_tag, keyword_tag, diagnosis_code_tag, language_tag, source_tag, document_type_tag, cpt_code_tag]
            self.result[filepath] = {
            'tags': [unique_name_tag, keyword_tag, diagnosis_code_tag, language_tag, corresponding_language_tag, source_tag, document_type_tag, cpt_code_tag],
            'file_path': filepath,
            'title': title,
            'short_url': short_url,
            'qr_code': qr_code
            }
            logger.debug(f"Tags for {filepath}: {self.result[filepath]}")

    def insert_tags(self):
        try:
            logger.debug(f'in insert tags, file to insert: {self.file_to_insert}')
            file_count = self._traverse_and_insert(self.file_to_insert)
        except Exception as e:
            logger.error(f'Error when inserting tags. {e}')
            raise
    # INSERTS THE TAGS INTO THE HTMLS
    def _traverse_and_insert(self, folder):
        file_count = 0
        for root, _, files in os.walk(folder):
            for file in files:
                if file != 'output_images' and file != ".DS_Store" and ".png" not in file:
                    file_count += 1
                    file_path = os.path.join(root, file)

                    # Read the existing content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    # Modify the existing content as needed
                    index = len(file_to_insert)
                    result_file_path = file_path[index:]
                    doctype_html_head_pattern = r"<!DOCTYPE\s+html>\s*<html>\s*<head>"
                    existing_content = re.sub(doctype_html_head_pattern, '', existing_content, flags=re.IGNORECASE)

                    valid_title = self.result[result_file_path]['title']
                    valid_title = valid_title.replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','') 
                    # Start creating the new content
                    new_content = '''<!DOCTYPE html
                        PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
                    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
                    <head>'''

                    # Write existing content up to and including existing meta tags
                    head_end_idx = existing_content.find("</head>")
                    head_content = existing_content[:head_end_idx]
                    new_content += head_content

                    #use title from spreadsheet instead of from pdf properties
                    new_content = re.sub(r'<title>.*?</title>',f'<title>{valid_title}</title>',new_content,flags=re.IGNORECASE)

                    # Insert tags - Specifics according to the JIRA tasks
                    for tag in self.result[result_file_path]['tags']:
                        #print(f'tag: {tag}')
                        if tag == "blank":
                            continue
                        if "ICD-10-CM" in tag:
                            logger.debug('in ICD-10')
                            if 'content="nan"' in tag:
                                old_tag = tag
                                tag = tag.replace('content="nan"', 'content=""')
                                # print(f'icd 10 code here, previous content: {old_tag}, new content: {tag.replace('content="nan"', 'content=""')}')
                                new_content += tag
                            else:
                                match = re.search(r'content="([^"]*)"', tag)
                                if match:
                                    content = match.group(1)
                                    #print(f'Original content: {content}')
                                    
                                    # Normalize spacing and handle both , and , 
                                    # Split by both , and , 
                                    parts = re.split(r',\s*', content)  # This will split on , or , 
                                    normalized_content = ', '.join(part.strip() for part in parts if part)  # Remove empty strings if any
                                    
                                    #print(f'Normalized content: {normalized_content}')
                                    
                                    # Rebuild the tag string with the cleaned content
                                    new_tag = re.sub(r'content="[^"]*"', f'content="{normalized_content}"', tag)
                                    new_tag = new_tag.replace(',', "")
                                    #print(f'Updated tag: {new_tag}')
                                    
                                    new_content += new_tag
                                else:
                                    print("No content found in the tag.")
                            continue
                        if ("CPT codes" in tag):
                            logger.debug('in CPT Codes')
                            if 'content="nan"' in tag:
                                new_content += tag.replace("nan", "")
                            else:
                                match = re.search(r'content="([^"]*)"', tag)
                                if match:
                                    content = match.group(1)
                                    #print(f'Original content: {content}')
                                    
                                    # Normalize spacing and handle both , and , 
                                    # Split by both , and , 
                                    parts = re.split(r',\s*', content)  # This will split on , or , with space
                                    normalized_content = ', '.join(part.strip() for part in parts if part)  # Remove empty strings if any
                                    
                                    #print(f'Normalized content: {normalized_content}')
                                    
                                    # Rebuild the tag string with the cleaned content
                                    new_tag = re.sub(r'content="[^"]*"', f'content="{normalized_content}"', tag)
                                    new_tag = new_tag.replace(',', "")
                                    #print(f'Updated tag: {new_tag}')
                                    new_content += new_tag
                                else:
                                    print("No content found in the tag.")
                            continue
                        if "Keywords" in tag:
                            logger.debug('in keywords')
                            if 'content="nan"' not in tag:
                                logger.debug('Keyword update detected - Overwriting Keyword Tag Now')
                                keyword_meta_pattern = r'<meta\s+name="Keywords"\s+content="[^"]*"\s*/?>'
                                keyword_to_replace = re.search(keyword_meta_pattern, existing_content)[0]
                                logger.debug(f'keyword to replace: {keyword_to_replace}')
                                new_content = new_content.replace(keyword_to_replace, "")
                                new_content += tag
                                continue
                            else:
                                continue
                        if "EN" in tag:
                            tag = tag.replace("EN", "eng")
                        if "SP" in tag:
                            tag = tag.replace("SP", "spa")
                        new_content += tag

                    
                    #new_content += existing_content[head_end_idx:]
                        
                    #getting the last image in the document, should be the QR code placeholder
                    existing_content_html = BeautifulSoup(existing_content, 'html.parser')     
                    images = existing_content_html.find_all('img')
                    qr_code_placeholder = images[-1]   
                    if replaceqrcodesandshorturls == 'True': 
                        logger.debug(f'starting qr codes and short urls')
                        #for some reason this text isn't always removed in the conversion so removing from the html string.
                        existing_content = existing_content.replace('[Health system  standard disclaimer for written materials.]','') \
                                            .replace('l!I@ Mytonomy @(j)','') \
                                            .replace('[health system standard disclaimer for written materials.]','') \
                                            .replace('If you have questions or need medical help contact us at: [health system standard for contact]','')
                        #creating html out of existing_content string
                        existing_content_html = BeautifulSoup(existing_content, 'html.parser')
                        #updating the text at the bottom of the document to include short url if found
                        short_url = self.result[result_file_path]['short_url']
                        short_url_placeholder_text = existing_content_html.find(string=lambda text: '[link]' in text)

                        if short_url != "" and (not isinstance(short_url, float) or not math.isnan(short_url)):
                            replacement_tag = f'<a href="{short_url}">{short_url}</a>'
                            existing_content = existing_content.replace('[link]',replacement_tag)
                            existing_content_html = BeautifulSoup(existing_content, 'html.parser')
                        else:

                            pattern = r"To learn more about.*?\[link\]"
                            pattern_es = r"Para.*?\[link\]"
                            # Use regex to remove [link] placeholder text
                            existing_content = re.sub(pattern, '', existing_content)
                            existing_content = re.sub(pattern_es, '', existing_content)
                            
                            if short_url_placeholder_text != None:
                                
                                url_prev_element = short_url_placeholder_text.previous_element
                                url_parent = short_url_placeholder_text.parent
                                if url_prev_element!= None: 
                                    #logger.debug(f' in prev element remvoal')
                                    if '[link]' in url_prev_element: 
                                        existing_content = existing_content.replace(str(url_prev_element), '')
                                

                                if url_parent != None: 
                                    #logger.debug(f' in parent remvoal')
                                    if '[link]' in url_parent: 
                                        existing_content = existing_content.replace(str(url_parent), '')
                                

                            existing_content_html = BeautifulSoup(existing_content, 'html.parser')


                        #starting QR Code insert
                        qr_code_url = self.result[result_file_path]['qr_code']

                        if qr_code_url != "" and (not isinstance(qr_code_url, float) or not math.isnan(qr_code_url)):
                            
                            #These are from the customer config file
                            qr_code_folder = configCustomer[f'{customer}']['qr_code_local_path']
                            html_images_folder = configCustomer[f'{customer}']['html_images_folder']

                            for qr_filename in os.listdir(qr_code_folder):
                                if qr_filename[-10:-5] == short_url[-5:]:

                                    source_file = os.path.join(qr_code_folder, qr_filename)
                                    target_file = os.path.join(html_images_folder, qr_filename)
            
                                    # Copy the qr code to the images folder
                                    shutil.copy(source_file, target_file)
                                    
                                    #Counting slashes to get qr code inserted correctly
                                    path_to_count = self.result[result_file_path]['file_path']
                                    slash_count = path_to_count.count('/')
                                    qr_prepend = ""
                                    for i in range(slash_count-1):
                                        qr_prepend += "../"            

                                    qr_code_placeholder['src'] = target_file.replace(str(html_images_folder).replace('Images',''), qr_prepend)
                                    qr_code_placeholder['width'] = '100'
                                    qr_code_placeholder['height'] = '100'

                                    a_tags = existing_content_html.find('a')
                                    if a_tags:
                                        center_div = existing_content_html.new_tag('div', **{'class': 'new_text', 'style': 'display: flex; justify-content: center; align-items: center; padding-bottom: 10pt'})
                                        parent_of_last_a = a_tags.parent
                                        parent_of_last_a['style'] = 'font-size: 12pt; padding-left:10pt;'
                                        center_div.append(qr_code_placeholder.parent)                                  
                                        center_div.append(parent_of_last_a)
                                        parent_of_last_a.extract
                                        qr_code_placeholder.parent.extract

                                        # looking for the text at the end of the document
                                        search_text = "IF YOU HAVE A MEDICAL EMERGENCY, CALL 911 OR GO TO THE EMERGENCY ROOM." 
                                        search_text_es = "LLAME AL 911 O VAYA A LA SALA DE EMERGENCIAS."
                                                        
                                        target_tag = existing_content_html.find(lambda tag: tag.string and search_text in tag.string)
                                        target_tag_es = existing_content_html.find(lambda tag: tag.string and search_text_es in tag.string)

                                        if target_tag:
                                            target_tag.name = 'p'
                                            target_tag.insert_before(center_div)

                                        if target_tag_es:
                                            target_tag_es.name = 'p'
                                            target_tag_es.insert_before(center_div)
                            
                        else: 
                            existing_content = existing_content.replace(str(qr_code_placeholder.parent.parent),'')
                            qr_code_wording = "Watch the video by using your phone's camera to click the QR code above."
                            qr_code_wording_es = "Vea el  video utilizando la cámara de su teléfono para darle  clic a el  código QR de arriba."
                            qr_code_wording_es2 = "Vea el video utilizando la cámara de su teléfono para darle clic a el código QR de arriba."
                            existing_content = existing_content.replace(qr_code_wording,'')
                            existing_content = existing_content.replace(qr_code_wording_es,'').replace(qr_code_wording_es2, '')
                            existing_content_html = BeautifulSoup(existing_content, 'html.parser')
                            qr_code_placeholder.parent.decompose()


                    if replaceqrcodesandshorturls == 'False':

                        link_pattern = r"To learn more about.*?\[link\]"
                        link_pattern_es = r"Para.*?\[link\]"
                        # Use regex to remove [link] placeholder text
                        existing_content = re.sub(link_pattern, '', existing_content)
                        existing_content = re.sub(link_pattern_es, '', existing_content)

                        #***********This should remove QR code wording and place holder **********
                        qr_code_wording = "Watch the video by using your phone's camera to click the QR code above."
                        qr_code_wording_2 = "Watch the video by using your phone camera to click on the QR Code above."
                        wording = "If you have questions or need medical help, contact us at"
                        qr_code_wording_es = "Vea el  video utilizando la cámara de su teléfono para darle  clic a el  código QR de arriba."
                        qr_code_wording_es2 = "Vea el video utilizando la cámara de su teléfono para darle clic a el código QR de arriba."
                        qr_code_wording_es3 = "Vea  el  video utilizando la  cámara  de  su teléfono para  darle  clic a  el  código QR  de  arriba."
                        more_info_wording_es = "¿Dónde puede obtener más información?"
                        more_info_wording_es1 = "¿Dónde puede  obtener más información?"
                        existing_content = existing_content.replace(qr_code_wording,'').replace(qr_code_wording_2,'').replace(qr_code_wording_es3,'').replace(wording,'')
                        existing_content = existing_content.replace(qr_code_wording_es,'').replace(qr_code_wording_es2, '').replace(more_info_wording_es,'').replace(more_info_wording_es1,'')
                        existing_content_html = BeautifulSoup(existing_content, 'html.parser')
                        images = existing_content_html.find_all('img')
                        qr_code_placeholder.decompose()
                    
                    search_text = "IF YOU HAVE A MEDICAL EMERGENCY, CALL 911 OR GO TO THE EMERGENCY ROOM." 
                    search_text_es = "LLAME AL 911 O VAYA A LA SALA DE EMERGENCIAS."
                                        
                    target_tag = existing_content_html.find(lambda tag: tag.string and search_text in tag.string)
                    target_tag_es = existing_content_html.find(lambda tag: tag.string and search_text_es in tag.string)

                    if target_tag:
                        target_tag.name = 'p'

                    if target_tag_es:
                        target_tag_es.name = 'p'

                    #adding disclaimer text
                    html_path = self.result[result_file_path]['file_path']
                    if configCustomer[f'{customer}']['include_disclaimer'] == 'True':
                        if html_path[-7:] != 'ES.html':
                            disclaimer = configCustomer[f'{customer}']['english_disclaimer']
                        else: 
                            disclaimer = configCustomer[f'{customer}']['spanish_disclaimer']
                        
                        disclaimer_p = existing_content_html.new_tag('p')
                        italic_text = existing_content_html.new_tag('i')
                        italic_text.string = disclaimer
                        disclaimer_p.append(italic_text)
                        existing_content_html.body.append(disclaimer_p)
                        
                        copyright_text = "©2024 Mytonomy, Inc. All rights reserved. Last updated May 2024."
                        copyright_p = existing_content_html.new_tag('p')
                        copyright_p.string = copyright_text
                        existing_content_html.body.append(copyright_p)


                    existing_content = existing_content_html.prettify() 
                    #adding the meta tags after beautiful soup to ensure correct ordering of name and content attributes
                    new_head_end_idx = existing_content.find("</head>")
                    new_content += existing_content[new_head_end_idx:]

                    # Validate the HTML
                    if self._is_html_valid(existing_content):
                        logger.info(f"HTML in {file_path} is valid.")
                    else:
                        logger.info(f"HTML in {file_path} is NOT valid.")

                    if self._is_html_valid(new_content):
                        logger.info(f"new_content HTML in {file_path} is valid.")
                    else:
                        logger.info(f"new_content HTML in {file_path} is NOT valid.")

                    '''
                    # Handle duplicate titles
                    pattern = r"<title>([^<]+)</title>"
                    match = re.search(pattern, existing_content)
                    patternLanguage = r'<meta\s+name="Language"\s+content="([^"]+)"\s*/>'
                    matchLanguage = re.search(patternLanguage, new_content)

                    if match:
                        title = match.group(1)
                        if "ES" in file_path:
                            if matchLanguage:
                                language = matchLanguage.group(1)
                                if language == "spa":
                                    valid_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip() + " (Spanish)"
                                elif language == "eng":
                                    valid_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        else:
                            valid_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        
                        # Ensure the title is unique
                        original_title = valid_title
                        counter = 1
                        while valid_title in self.used_titles:
                            valid_title = f"{original_title}_{counter}"
                            counter += 1
                        self.used_titles.add(valid_title)
                        
                        directory, original_filename = os.path.split(file_path)
                        file_extension = os.path.splitext(original_filename)[1]

                        new_file_path = os.path.join(directory, valid_title + file_extension)
                    '''

                    # new code for renaming files.
                    directory, original_filename = os.path.split(file_path)
                    file_extension = os.path.splitext(original_filename)[1]

                    new_file_path = os.path.join(directory, valid_title + file_extension)
                    
                    with open(file_path, 'w', encoding="utf-8") as f:
                        f.write(new_content)

                    os.rename(file_path, new_file_path)

                    process_single_html_file(new_file_path, new_file_path)

                    
                    # Replace &amp; with & in the file content
                    with open(new_file_path, 'r+', encoding="utf-8") as f:
                        content = f.read().replace('&amp;', '&')
                        #content = f.read().replace('tagstitle', '')
                        #print(content)
                        f.seek(0)
                        f.write(content)
                        f.truncate()

        return file_count
    
    # DETERMINES IF THE HTML IS VALID
    def _is_html_valid(self, content):
        try:
            html.fromstring(content)
            return True
        except Exception as e:
            logger.error(f"HTML validation error: {e}")
            return False
    

file = os.path.join(configCustomer[f'{customer}']['local_folder_path'], f"EpicHtmlRequirements/{configCustomer[f'{customer}']['spreadsheet_name']}")  
file_to_insert = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/HTML')
print("INSIDE META TAG GENERATOR FILE TESTING FOR STDOUT")
#print(file)
#print(file_to_insert)
try:
    logger = init_logging('LOGGING_MetaTagInsertion', 'Tag Insertion')
    generator = MetaTagGenerator(file, file_to_insert)
    generator.generate_tags()  
    generator.insert_tags()
except Exception as e:
    logger.error(f'Error detected when generating and inserting meta tags. {e}')
    sys.exit(1)
