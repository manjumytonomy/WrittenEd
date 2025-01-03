import fitz  # PyMuPDF library 
from bs4 import BeautifulSoup
import os
from extract_text import extract_text_with_positions, replace_special_characters, extract_text_properties
from onepager_extract_text import one_pager_extract_text_with_positions, one_pager_extract_text_properties
from extract_images import extract_images_and_coordinates
from onepager_extract_images import one_pager_extract_images_and_coordinates
import configparser
import shutil
import re
import logging
import sys
from logging.handlers import RotatingFileHandler
#POC Change
from pdf_to_html_processor import process_pdf_to_html
from fuzzywuzzy import fuzz
#POC Change

# Buffer for skipped/removed text
text_removed = []

# Used in generate_html method for removing invalid symbols/text
invalid_text = ['~', ',.', '.,', '>', '<', '-.', ":'", 'r:', '(!', '---', '--', 'lnova™','□', '®', '@1@', '[!!', 'l @Mytonomy', 'l i Mytonomy',  '@1@ Mytonomy @ !ID', '@® M\1tonomy @ \'1', '1!1@ Mytonomy @100', '@1@ Mytonomy @', 'l!I@ Mytonomy @(,!)', '@® M,,tonomy @ ,,', 'j ¡ Mytonomy', '! I Mytonomy', '~®Mytonomy @~','l!I@ Mytonomy @100', '@®Mytonomy @í,!1', '[!)@ Mytonomy @~', '@1@ Mytonomy @®', 'i : :-;>,Ji', 'I ·\ : ! . ;¥/ ','¥', '! i Mytonomy', '~®Mytonomy @~', '@@M t @OO y onomy', '[health system standard disclaimer for written materials.]', 'Si tiene preguntas o requiere asistencia médica, póngase en contacto con nosotros: [Información de contacto estándar del sistema de salud]', 'Watch the video by using your phone camera to click on the QR Code above.']

# Used in generate_html method for removing unwanted text after block extraction (preprocessing before adding to html_content)
unwanted_text = [
 'Where Can You Learn More?', 
 'Where Can You Learn More',
 'Dónde puedes obtener más información', 
 '¿Dónde puede obtener más información?', 
 '¿Dónde puede  obtener más información?',
 'Dónde puede obtener más información',
  
 'If you have questions or need medical help, contact us at [Health system standard for contact]',
 'If you have questions or need medical help contact us at [Health system standard for contact]', 
 'If you have questions or need medical help, contact us at',
 'If you  have  questions or need  medical help,  contact  us at:   (Health  system  standard  for  contact)'
 '[Health system standard for contact]', 
 '(Health system standard for contact)',

 'Si tiene preguntas o requiere asistencia médica, póngase en contacto con nosotros: [Información de contacto estándar del sistema de salud]', 
 'Si tienes preguntas o requieres asistencia médica, ponte en contacto con nosotros: [información de contacto estándar del sistema de salud]',
 'Si tiene  preguntas o r equiere a sistencia  médica, póngase  en  contacto con nosotros: [Información de  contacto estándar del  sistema  de  salud]',
 'Si tienes preguntas o necesitas asistencia médica, ponte en contacto con nosotros a través de:',
 'Información de contacto estándar del sistema de salud', 
 
 '[Health system standard disclaimer for written materials.]', 
 '[Health system  standard disclaimer for written materials.]',
 '[Health system standard disclaimer for  written materials.]',
 '(Health  system  standard  disclaimer for  written  materials.)',
 '(Health system standard disclaimer for written materials.)',
 '[health system standard disclaimer for written materials.] This document meets our standards for health literacy between levels 5 to 7. People with disabilities should not have difficulty reading this document',
 '[Descargo de responsabilidad estándar del sistema de salud para el material escrito]. Este documento cumple nuestras normas de alfabetización en salud entre los niveles 5 a 7. Las personas con discapacidad no deberían tener dificultades para leer este documento',
 '[Aviso legal estándar del sistema médico para documentos.] Este documento cumple nuestras normas de conocimientos sobre salud entre los niveles de 5 a 7. Las personas con discapacidad no deberían tener dificultades para leer este documento', 
  
 'Watch the video by using your phone camera to click on the QR Code above',
 '(enter the QR code''s URL',
 'Vea el video utilizando la cámara de su teléfono para darle clic a el código QR de arriba',
 
 'To learn more about Preparing for Colonoscopy, go to',  
 'Para más información sobre Preparación para la colonoscopia, vaya a',  
 'Para más información sobre Recuperación Tras Una Colonoscopia, vaya a',
  
 'To learn more about Preparing for Endoscopy, go to', 
 'To learn more about Recovery After Endoscopy, go to', 
 'Para más información sobre Recuperación después la endoscopia, vaya a', 
 
 'To learn more about Gastroesophageal Reflux Disease GERD, go to', 
 'Para más información sobre Enfermedad por reflujo gastroesofágico (ERGE), vaya a'
]

# Used in remove_unwanted_text method to remove html tags by substring comparison
unwanted_text_unique = [
 #1 pagers
 '(health system standard for contact)',
 'if you have a medical emergency, call 911 or go to the emergency room.-',
 'if you have a medical emergency, call 911 or go to the emergency room.',
 '(health system standard disclaimer for written materials.) this document meets our standards for health literacy between levels 5 to 7.',
 'this document meets our standards for health literacy between levels 5 to 7. (edited) '
 'if you have a  medical  emergency, call 91 1 or g o  to  the  emergency room.',
 'si tiene preguntas o requiere asistencia médica, póngase en contacto con nosotros: (información de contacto estándar del sistema de salud)',
 '(descargo de responsabilidad estándar del sistema de salud para el material escrito).',
 'Para más información sobre Lesión en el tobillo, vea el video. Apunte con la cámara de su teléfono al código QR en la esquina superior derecha y haga clic en el enlace o escriba este enlace en su navegador web: (ingresar la URL del código QR)',
 '(health system standard disclaimer for written materials.) this document meets our standards for health literacy between levels 5 to 7. [keep the “reads easy"',


 'where can you learn more', 
 'dónde puedes obtener más información', 
 'dónde puede obtener más información',
 '¿Dónde puede obtener más información?',
 '(insert link)',
 
 'if you have questions or need medical help, contact us at [health system standard for contact]',
 'if you have questions or need medical help contact us at: [health system standard for contact]',
 'if you have questions or need medical help contact us at:[health system standard for contact]',
 'if you have questions or need medical help, contact us at: [health system standard for contact]',
 'si tiene preguntas o requiere asistencia médica, póngase en contacto con nosotros: [información de contacto estándar del sistema de salud]', 
 'si tienes preguntas o requieres asistencia médica, ponte en contacto con nosotros: [información de contacto estándar del sistema de salud]',
 'si tienes preguntas o necesitas asistencia médica, ponte en contacto con nosotros a través de:',
 
 '[health system standard disclaimer for written materials.] this document meets our standards for health literacy between levels 5 to 7. people with disabilities should not have difficulty reading this document',
 '[descargo de responsabilidad estándar del sistema de salud para el material escrito]. este documento cumple nuestras normas de alfabetización en salud entre los niveles 5 a 7. las personas con discapacidad no deberían tener dificultades para leer este documento',
 '[aviso legal estándar del sistema médico para documentos.] este documento cumple nuestras normas de conocimientos sobre salud entre los niveles de 5 a 7. las personas con discapacidad no deberían tener dificultades para leer este documento', 
 
 'watch the video by using your phone camera to click on the qr code above',
 'vea el video utilizando la cámara de su teléfono para darle clic a el código qr de arriba',
 
 'to learn more about preparing for colonoscopy, go to',  
 'para más información sobre preparación para la colonoscopia, vaya a',  
 'para más información sobre recuperación tras una colonoscopia, vaya a',
  
 'to learn more about preparing for endoscopy, go to', 
 'to learn more about recovery after endoscopy, go to', 
 'para más información sobre recuperación después la endoscopia, vaya a', 
 
 'to learn more about gastroesophageal reflux disease gerd, go to', 
 'para más información sobre enfermedad por reflujo gastroesofágico (erge), vaya a'
]

emergency_line_match = [["if", "you", "have", "medical", "emergency", "room"],
                        ["si", "tiene", "una", "emergencia", "médica", "emergencias"],
                        ["si", "tienes", "una", "emergencia", "médica", "emergencias"]]
                                

# Configuration
config = configparser.ConfigParser()
config.read('../config.ini')
#config.read(r'C:\krishna\WrittenEd-PDFToHtmlConverter\WrittenEd-PDFToHtmlConverter\src\config.ini')

customer = config['CUSTOMER']['customer_name']
removed_unwanted_text_flag = config['OPTION_FLAGS']['removeunwantedtext']
skip_one_pagers_flag = config['OPTION_FLAGS']['skiponepagers']
print(f"THIS IS THE ONE PAGER FLAG PRINTED OUT {skip_one_pagers_flag}")
configCustomer = configparser.ConfigParser()
configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')
#test = configCustomer.read(r'C:\krishna\WrittenEd-PDFToHtmlConverter\WrittenEd-PDFToHtmlConverter\src\CustomerConfigs\AAH_Oct18_2024_config.ini')

script_dir = os.path.dirname(os.path.abspath(__file__))   # Get the absolute path of the directory that this file is in
project_dir = os.path.dirname(script_dir)                 # Go up one directory


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


'''This is the main file in the program. It is the file that generates the HTML code by envoking functions from the extract_text
and extract_images python files. This class generates the HTML by first defining the structure of the HTML along with attributes. Then the function 
iterates through a given PDF page by page and invokes the extract_text and extract_images file functions to generate HTML 
lines with the extracted information.'''


class MytonomyPDFConverter:



    #POC Change - added grouped_df as a constructor parameter
    def __init__(self, pdf_path, output_html_path, one_pager_doc, grouped_df):
    #POC Change - added grouped_df as a constructor parameter  
        print("initialized")
        self.pdf_path = pdf_path
        self.output_html_path = output_html_path
        #self.first_image_coords = [(None, None, None, None)]
        #POC Change
        self.grouped_df = grouped_df
        self.one_pager_doc = one_pager_doc

        self.extract_metadata()

    def extract_metadata(self):
        doc = fitz.open(self.pdf_path)
        metadata = doc.metadata
        self.title = metadata.get('title')
        self.author = metadata.get('author')
        self.subject = metadata.get('subject')
        self.keywords = metadata.get('keywords')

    def get_title(self):
        return self.title
    
    def get_author(self):
        return self.author

    def get_subject(self):
        return self.subject
    
    def get_keywords(self):
        return self.keywords
    
    def replace_urls_with_hyperlinks(self, html_content):
        pattern = r'(https?://\S+)(?=<\/p>)'
  
        def replace_with_hyperlink(match):
            url = match.group(0)
            clean_url = url.replace(' ', '')
            new_url = " " + clean_url
            return f'<a href="{clean_url}">{new_url}</a>'
        
        # Replace URLs with hyperlinks
        html_content = re.sub(pattern, replace_with_hyperlink, html_content)
        html_content = re.sub(r'(<a href="https?://\S+">https?://\S+)(</p>)</a>', r'\1</a>\2', html_content)

        return html_content

    
    def adjust_image_positions(self, html_content):
        """
        Finds the <p><span><img> tag inside <ul id="l1"> elements in the given HTML content,
        only if the width and height of the <img> tag are below 35.
        Copies those image tags and places them outside of the entire <ul> tag.
        """
        
        # Define regex patterns
        ul_pattern = re.compile(r'(<ul id="l1"[^>]*>.*?</ul>)', re.DOTALL)
        img_pattern = re.compile(r'<p style="text-indent: 0pt;text-align: left;">\s*<span>\s*<img\s+width="(\d+(\.\d+)?)"\s+height="(\d+(\.\d+)?)".*?/>\s*</span>\s*</p>', re.DOTALL)
        
        # Find all <ul id="l1"> sections
        updated_html_content = ""
        last_pos = 0
        
        for ul_match in ul_pattern.finditer(html_content):
            ul_content = ul_match.group(1)
            ul_start, ul_end = ul_match.span()
            
            # Search for <p><span><img> tag within this <ul> content
            img_matches = img_pattern.findall(ul_content)
            img_tags_to_move = []
            
            # Check if width and height are below 35 and collect those tags
            for img_match in img_matches:
                width = float(img_match[0])
                height = float(img_match[2])
                
                if width < 35 and height < 35:
                    img_tag = re.search(r'<p style="text-indent: 0pt;text-align: left;">\s*<span>\s*<img\s+width="{}"\s+height="{}".*?/>\s*</span>\s*</p>'.format(img_match[0], img_match[2]), ul_content, re.DOTALL).group(0)
                    img_tags_to_move.append(img_tag)
                    # Remove the image tag from the UL content
                    ul_content = ul_content.replace(img_tag, "")
            
            # Construct the updated <ul> content
            updated_ul_content = ul_content
            
            # Add the remaining <ul> content with image tags removed
            updated_html_content += html_content[last_pos:ul_start] + updated_ul_content
            
            # Add the collected image tags outside of the <ul>
            if img_tags_to_move:
                updated_html_content += "\n" + "\n".join(img_tags_to_move)
            
            last_pos = ul_end
        
        # Add any remaining HTML content after the last <ul> tag
        updated_html_content += html_content[last_pos:]

        return updated_html_content


    def confirm_subheadings(self, html_content):
        """
        This function goes through and detects every icon in the HTML. If the next element is not an <h2> tag,
        it replaces that element with the correct <h2> tag format. It handles <p> and <h3> tags because some times they are not converted right, and then converts them to <h2>
        only if the image width and height are both less than 35.
        """
        
        # Regular expression to match the <img> tag pattern
        img_tag_pattern = r'<p style="text-indent: 0pt;text-align: left;">\s*<span>\s*<img\s+width="(\d+(\.\d+)?)"\s+height="(\d+(\.\d+)?)".*?/>\s*</span>\s*</p>'
        
        # Find all matches in the HTML content
        img_matches = list(re.finditer(img_tag_pattern, html_content))
        
        # List to store replacements
        replacements = []
        
        # Line limit to check after the <img> tag
        line_limit = 1
        
        for img_match in img_matches:
            img_tag = img_match.group(0)
            img_width = float(img_match.group(1))
            img_height = float(img_match.group(3))
            
            # Check if the image is an icon (width and height both less than 35)
            if img_width < 35 and img_height < 35:
                img_end_pos = img_match.end()
                
                # Extract the content starting after the <img> tag
                following_html = html_content[img_end_pos:]
                
                # Extract lines up to the line limit
                lines = following_html.split('\n', line_limit + 1)
                limited_html = '\n'.join(lines[:line_limit + 1])
                
                # Look for <p> or <h3> tags within the limited HTML
                p_tag_pattern = r'<p\b[^>]*>(.*?)<\/p>'
                h1_tag_pattern = r'<h1\b[^>]*>(.*?)<\/h1>'
                h3_tag_pattern = r'<h3\b[^>]*>(.*?)<\/h3>'
                
                p_tag_match = re.search(p_tag_pattern, limited_html, re.DOTALL)
                h1_tag_match = re.search(h1_tag_pattern, limited_html, re.DOTALL)
                h3_tag_match = re.search(h3_tag_pattern, limited_html, re.DOTALL)
                
                if p_tag_match:
                    p_text = p_tag_match.group(1).strip()
                    print(f'p text: {p_text}')
                    # Create the new <h2> tag with extracted <p> text
                    new_h2_tag = f'<h2 style="color: #000000;">{p_text}</h2>'
                    # Replace <p> tag with new <h2> tag
                    new_p_tag = f'{img_tag}\n{new_h2_tag}'
                    replacements.append((img_match.start(), img_end_pos + p_tag_match.end(), new_p_tag))
                if h1_tag_match:
                    h1_text = h1_tag_match.group(1).strip()
                    print(f'h1 text: {h1_text}')
                    # Create the new <h2> tag with extracted <h3> text
                    new_h2_tag = f'<h2 style="color: #000000;">{h1_text}</h2>'
                    # Replace <h3> tag with new <h2> tag
                    new_h1_tag = f'{img_tag}\n{new_h2_tag}'
                    replacements.append((img_match.start(), img_end_pos + h1_tag_match.end(), new_h1_tag))
                if h3_tag_match:
                    h3_text = h3_tag_match.group(1).strip()
                    print(f'h3 text: {h3_text}')
                    # Create the new <h2> tag with extracted <h3> text
                    new_h2_tag = f'<h2 style="color: #000000;">{h3_text}</h2>'
                    # Replace <h3> tag with new <h2> tag
                    new_h3_tag = f'{img_tag}\n{new_h2_tag}'
                    replacements.append((img_match.start(), img_end_pos + h3_tag_match.end(), new_h3_tag))
        
        # Apply all replacements to the HTML content
        for start_pos, end_pos, new_tag in reversed(replacements):
            html_content = html_content[:start_pos] + new_tag + html_content[end_pos:]
        
        return html_content

    def remove_unwanted_text(self, html_content):
        """
        This function removes tags from the html content, if the tags contain unwanted text
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Iterate over the tags we are interested in
        for tag in soup.find_all(['h1', 'h2', 'h3', 'span', 'p']):
            # Design idea: Convert each tag text to lowercase, removing extra whitespace to compare directly with unwanted_text_unique strings
            tag_content = re.sub(r'\s+', ' ', tag.get_text().strip().lower())
            # Check if any unwanted text is in the tag's content
            if any(unwanted_text in tag_content for unwanted_text in unwanted_text_unique):
                tag.decompose()  # Remove the tag if it contains unwanted text

        html_content = soup.prettify()
        return html_content
    #function for consolidating h1 tags and replace with a single h1 tag
    def merge_h1_tags(self, html):
        # Parse the HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all h1 tags
        h1_tags = soup.find_all('h1')
        
        # If there are no h1 tags, return the original HTML
        if not h1_tags:
            return soup.prettify()
        
        # Combine the text of all h1 tags
        merged_h1_text = ' '.join(h1.get_text() for h1 in h1_tags)
        
        # Create a new h1 tag with the merged text
        new_h1_tag = soup.new_tag('h1')
        new_h1_tag.string = merged_h1_text
        
        # Replace the first h1 tag with the new h1 tag
        first_h1_tag = h1_tags[0]
        first_h1_tag.replace_with(new_h1_tag)
        
        # Remove the remaining h1 tags
        for h1 in h1_tags[1:]:
            h1.decompose()
        
        # Return the modified HTML
        return soup.prettify()
    
    def adjust_images_in_bullets(self, html_content):
        """
        This function processes <img> tags where width and height are greater than 35. It checks for an optional <p> tag
        with an <i> tag following the image and then searches for a <ul> tag to determine where to insert the image tag 
        with or without the <p><i> content.
        """
        
        # Regular expression patterns
        img_tag_pattern = r'<p style="text-indent: 0pt;text-align: left;">\s*<span>\s*<img\s+width="(\d+(\.\d+)?)"\s+height="(\d+(\.\d+)?)".*?/>\s*</span>\s*</p>'
        p_tag_pattern = r'<p\b[^>]*>(.*?)<\/p>'
        i_tag_pattern = r'<i\b[^>]*>.*?<\/i>'
        ul_start_tag_pattern = r'<ul\b[^>]*>'
        li_start_tag_pattern = r'<li data-list-text="•">'
        
        # Find all image tags in the HTML content
        img_matches = list(re.finditer(img_tag_pattern, html_content))
        
        # List to store replacements
        replacements = []
        
        # Line limit to check after the <img> tag
        line_limit = 1
        
        for img_match in img_matches:
            img_tag = img_match.group(0)
            img_tag = img_tag.replace('"', '').replace("'", "")
            img_width = float(img_match.group(1))
            img_height = float(img_match.group(3))
            
            # print(f"Found image tag: {img_tag}")
            # print(f"Image width: {img_width}, Image height: {img_height}")
            
            # Check if the image width and height are greater than 35
            if img_width > 35 and img_height > 35:
                img_start_pos = img_match.start()
                img_end_pos = img_match.end()
                
                # print(f"Image tag starts at: {img_start_pos}, ends at: {img_end_pos}")
                
                # Extract the content starting after the <img> tag
                following_html = html_content[img_end_pos:]
                
                # Extract lines up to the line limit
                lines = following_html.split('\n', line_limit + 1)
                limited_html = '\n'.join(lines[:line_limit + 1])
                
                # print(f"Limited HTML after image tag:\n{limited_html}")
                
                # Look for <p> tags and <i> tags within the limited HTML
                p_tag_match = re.search(p_tag_pattern, limited_html, re.DOTALL)
                i_tag_match = re.search(i_tag_pattern, limited_html, re.DOTALL)

                #fix for not processing images that are not part of p_tag or i_tag, then 
                #it should not change the position - KGK Fix
                if not p_tag_match or not i_tag_match:
                    continue
                if p_tag_match:
                    p_html = p_tag_match.group(0)
                    p_end_pos = img_end_pos + p_tag_match.end()
                    # print(f"Found <p> tag:\n{p_html}")
                    
                    # If <i> tag is present inside <p> tag
                    if i_tag_match:
                        i_end_pos = p_end_pos
                        # print(f"Found <i> tag. End position updated to: {i_end_pos}")
                    else:
                        i_end_pos = img_end_pos
                        # print("No <i> tag found within <p> tag.")
                else:
                    p_html = ""
                    i_end_pos = img_end_pos
                    # print("No <p> tag found.")
                
                # Extract content starting from the end position after <p> or <img> tag
                following_content_after_p_or_img = html_content[i_end_pos:]
                
                # Look for <ul> start tag with a line limit of 1 after i_end_pos
                limited_html_after_p_or_img = following_content_after_p_or_img.split('\n', line_limit + 1)
                limited_html_after_p_or_img = '\n'.join(limited_html_after_p_or_img[:line_limit + 1])
                
                ul_start_match = re.search(ul_start_tag_pattern, limited_html_after_p_or_img, re.DOTALL)
                li_start_match = re.search(li_start_tag_pattern, limited_html_after_p_or_img, re.DOTALL)
                
                # if li_start_match:
                #     print("LI START MATCH")
                    
                if ul_start_match or li_start_match:
                    # Search for the closing </ul> tag in the entire HTML content from the i_end_pos
                    ul_end_pos = html_content.find('</ul>', i_end_pos)
                    # print(f'ul end pos: {ul_end_pos}')
                    
                    if ul_end_pos != -1:
                        ul_complete = html_content[i_end_pos:ul_end_pos + len('</ul>')]
                        # print(f"Found <ul> tag. Content till </ul>:\n{ul_complete}")
    
                        replacement_html = f'{ul_complete}\n{html_content[img_start_pos:img_end_pos]}{p_html}\n'
                        # print(f'replacement_html: {replacement_html}')
                        replacements.append((img_start_pos, ul_end_pos + len('</ul>'), replacement_html))
                #     else:
                #         print("No </ul> tag found after <ul> tag.")
                # else:
                #     print("No <ul> start tag found within the line limit after image tag.")
        
        # print(f'replacements: {replacements}')
        # Apply all replacements to the HTML content
        for start_pos, end_pos, new_html in reversed(replacements):
            html_content = html_content[:start_pos] + new_html + html_content[end_pos:]
            # print(f"Replacing content from {start_pos} to {end_pos}")
            # print(f"New HTML snippet:\n{new_html}")
        
        return html_content

    
    def align_subheadings(self, html_content):
        """
        This function goes through and detects every icon in the HTML, and then if there is a subheading after it, the subheading h2 tag gets added into the <p> tag with the icon to ensure good visability
        on all page windows
        """
        
        # Lines to check after detected the img_tag_pattern for the h2 tag to account for empty <p> tags that may be there
        line_limit = 2
        # Regular expression to match the <img> tag and capture width and height attributes
        img_tag_pattern = r'<p style="text-indent: 0pt;text-align: left;">\s*<span>\s*<img\s+width="(\d+(\.\d+)?)"\s+height="(\d+(\.\d+)?)".*?/>\s*</span>\s*</p>'
        
        # Find all matches in the HTML content
        img_matches = list(re.finditer(img_tag_pattern, html_content))
        
        # List to store replacements
        replacements = []
        
        for img_match in img_matches:
            img_tag = img_match.group(0)
            img_width = float(img_match.group(1))
            img_height = float(img_match.group(3))
            
            # Check if the image is an icon - only then we should do the next steps
            if img_width < 35 and img_height < 35:
                img_end_pos = img_match.end()
                # Extract the content starting after the <img> tag
                following_html = html_content[img_end_pos:]
                
                # Extract lines up to the line limit
                lines = following_html.split('\n', line_limit + 1)
                limited_html = '\n'.join(lines[:line_limit + 1])
                
                # Look for <h2> tag within the limited HTML
                h2_tag_pattern = r'<h2\b[^>]*>(.*?)<\/h2>'
                h2_tag_match = re.search(h2_tag_pattern, limited_html, re.DOTALL)
                
                if h2_tag_match:
                    h2_text = h2_tag_match.group(1).strip()
                    h2_start_pos = h2_tag_match.start()
                    h2_end_pos = h2_tag_match.end()
                    
                    # Calculate the new end position to include the <h2> tag
                    new_end_pos = img_end_pos + h2_end_pos
                    
                    # Create the new <p> tag with <img> and <h2> text
                    img_tag_with_h2 = re.sub(r'(<span>\s*<img\s+[^>]+/>\s*</span>)', rf'\1<span class="h2">{h2_text}</span>', img_tag)
                
                    # Create the new <p> tag
                    new_p_tag = f'{img_tag_with_h2}'
                    
                    # Replace the entire segment including <img> and <h2> tag with the new <p> tag
                    replacements.append((img_match.start(), new_end_pos, new_p_tag))
        
        # Apply all replacements to the HTML content
        for start_pos, end_pos, new_tag in reversed(replacements):
            html_content = html_content[:start_pos] + new_tag + html_content[end_pos:]
        
        return html_content
    
    def remove_footer_image(self, html_content):
        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all <p> tags
        p_tags = soup.find_all('p')

        # Check the last <p> tag if it contains an image with dimensions < 60x60
        if p_tags:
            p_tags_to_parse = [p_tags[-1], p_tags[-2]] # Parse only the last few p_tags for footer cleanup
            for p_tag in p_tags_to_parse:
                img_tag = p_tag.find('img')
                if img_tag:
                    width = float(img_tag.get('width', 0))
                    height = float(img_tag.get('height', 0))
                    # Remove <p> tag if the image dimensions are less than 60x60
                    if width < 60 and height < 60:
                        p_tag.decompose()

        # Get the modified HTML
        return str(soup)


    def generate_html(self):
        global text_removed
        try:
            doc = fitz.open(self.pdf_path)
            count = 1

            title = self.get_title()
            title = title.replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','')
            # print(f"title for filepath: {self.pdf_path} is {title} ")
            author = self.get_author()
            subject = self.get_subject()
            keywords = self.get_keywords()
            if keywords.endswith(','):
                keywords = keywords[:-1]  

            # Adjusting folder positions for css and js based on self.pdf_path
            start_index = self.pdf_path.find('DownloadedPDFs')
            if start_index != -1:
                start_index += len('DownloadedPDFs')
                path_segment = self.pdf_path[start_index:]

                count_slashes = path_segment.count('/')
            css_prepend = ""
            js_prepend = ""
            for i in range(count_slashes-2):
                css_prepend += "../"
                js_prepend += "..\\"


            # Main output variable
            html_content = (
                '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'''
                '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">'
                '<body>'
            )

            in_list = False
            doc_type_tracking = ""
            title_header_text = title
            title_found = False
            
            # Main processing
            for page_num, page in enumerate(doc):
                if self.one_pager_doc:
                    images_info = one_pager_extract_images_and_coordinates(self.pdf_path, page_num, 1)
                else:
                    images_info = extract_images_and_coordinates(self.pdf_path, page_num, 1) 

                # if the documents are one pagers, we call the one pager text function instead 
                if self.one_pager_doc:
                    blocks, removed_text = one_pager_extract_text_with_positions(page, page_num, images_info, self.pdf_path)
                else:
                    blocks, removed_text = extract_text_with_positions(page, page_num, images_info, self.pdf_path)
                
                text_removed = removed_text
                unprocessed_combined_elements = []

                # Combine text blocks and image info into the desired tuple structure
                for block in blocks:
                    try:
                        coords = block[:4]
                        content = block[4]
                        elem_type = 'text'
                        alignment = block[-1]
                        unprocessed_combined_elements.append((coords, content, elem_type, alignment))
                    except IndexError as e:
                        logging.error(f"IndexError for block {block}: {e}")
                        raise

                for image in images_info:
                    coords = image[1]
                    content = image[0]  # Blank content for images
                    elem_type = 'image'
                    alignment = image[-1]
                    unprocessed_combined_elements.append((coords, content, elem_type, alignment))

                # Sort by y0 coordinate
                unprocessed_combined_elements.sort(key=lambda x: x[0][1])
                
                # THIS IS ALL NEW CODE TO SORT THE IMAGE CAPTIONS
                combined_elements = []
                threshold = 5
                captions = []

                # Debugging
                # print("I will now be printing out the list of unordered elements to see what it looks like : ")
                # for i, element in enumerate(unprocessed_combined_elements):
                #     print(element)

                # Convert unprocessed_combined_elements to combined_elements
                while unprocessed_combined_elements:
                    current = unprocessed_combined_elements.pop(0)
                    combined_elements.append(current)

                    if current[2] == 'image':
                        current = tuple(str(c).replace('"', '').replace("'", "").replace('&',' and ').replace(':','_').replace('’','') if isinstance(c, str) else c for c in current)
                        #logger.debug(f'image tuple {current}')
                        
                    # If the current element is an image, find any text elements that should be its caption
                    if current[2] == 'image' and current[3] == "right":
                        current_bbox = current[0]
                        #current_alignment = current_bbox[-1]
                        bottom_y_coordinate = current_bbox[3]

                        for i, elem in enumerate(unprocessed_combined_elements):
                            compare_bbox = elem[0]
                            top_y_coordinate = compare_bbox[1]
                            compare_type = elem[2]
                            compare_alignment = elem[3]

                            if compare_type == 'image':
                                continue
                            
                            if compare_alignment == 'left':
                                continue

                            # Caption identification code logic needs to be modified if PDF structure changes
                            if abs(top_y_coordinate - bottom_y_coordinate) < 12:
                                captions.append(unprocessed_combined_elements[i][1])
                                combined_elements.append(unprocessed_combined_elements[i])
                                unprocessed_combined_elements.pop(i)
                                break


                logger.debug(f'PRINTING ALL COMBINED ELEMENTS TO CHECK ORDER')
                for element in combined_elements:
                    logger.debug(element)
                
                # Process combined_elements
                for i, element in enumerate(combined_elements):
                    coords, content, elem_type, alignment = element
                    y0, y1 = coords[1], coords[3]

                    if elem_type == 'text':
                        # Check for potential overlap with the next element
                        if i + 1 < len(combined_elements):
                            next_element = combined_elements[i + 1]
                            next_coords, next_content, next_elem_type, next_alignment = next_element
                            next_y0 = next_coords[1]
                        block_rect = fitz.Rect(coords)
                        block_text = content.strip()

                        if next_elem_type == 'image' and next_y0 <= y1:
                            # Insert the image first if it overlaps with the text block
                            x0, y0, x1, y1 = next_coords
                            width = x1 - x0
                            height = y1 - y0

                            # Only give priority to the image if it is a subheading icon - otherwise add the image like normal
                            # 35x35 is approximately the dimension of subheading icons 
                            if width < 35 and height < 35:
                                html_content += f'<p style="text-indent: 0pt;text-align: left;"><span><img width="{width}" height="{height}" alt="image" src="{next_content}" style="float: left; margin-right: 10px;" /></span></p>\n'
                                if (i+1) < len(combined_elements):
                                    combined_elements.pop(i + 1)  # Remove the image element after adding

                        if block_text:
                            text = replace_special_characters(block_text)
                            
                            if text in captions:
                                #css style for caption text introduced
                                html_content += f'<p class=cap>{text}</p>\n'
                                continue
                            ######################## WAM-89 fixes starts ####################################################
                            if ("Page |" in text) or ("Página |" in text) or ("Página" in text) or ("|Page ") in text:
                                continue
                            ######################## WAM-89 fixes End ####################################################

                            # Remove invalid text (when there are few spaces in text)
                            if text.count(" ") < 5:
                                # Search for invalid text
                                invalid_text_check = False
                                for item in invalid_text:
                                    if item in text:
                                        invalid_text_check = True
                                        break
                                
                                if "o" == text or (('00' in text) and ('100' not in text)) or invalid_text_check:
                                    print(f"INVALID TEXT DETECTED: {text}")
                                    text_removed.append(text)
                                    continue
                                
                                if removed_unwanted_text_flag == 'True':
                                    # Search for unwanted text
                                    unwanted_text_check = False
                                    for item in unwanted_text:
                                        if item in text:
                                            unwanted_text_check = True
                                            break
                                    
                                    if unwanted_text_check:
                                        print(f"UNWANTED TEXT DETECTED: {text}")
                                        text_removed.append(text)
                                        continue

                            starting_without_bullet_point = False
                            if text.startswith('•') or text.startswith('&#8226;') or '•' in text or '&#8226;' in text:
                                if not text.startswith('•') or text.startswith('&#8226;'):
                                    starting_without_bullet_point = True
                                # Split the bullet points into separate list items
                                bullet_points = text.split('•')
                                if bullet_points[0].strip() == '':
                                    bullet_points = bullet_points[1:]  # Remove the first empty item if split occurred at the start
                                for bullet in bullet_points:
                                    if bullet.strip():
                                        #next three lines are new
                                        if starting_without_bullet_point:
                                            html_content += f'<p>{bullet.strip()}</p>\n'
                                            starting_without_bullet_point = False
                                            continue
                                        if '·' in bullet.strip():
                                            print("invalid character detected")
                                            continue
                                        if not in_list:
                                        ########################## Fix for WAM-93 Starts ###########################
                                            if html_content.endswith('<br><br>'):
                                                html_content = html_content[:-8]  
                                        ########################## Fix for WAM-93 Ends ###########################
                                            html_content += '<ul id="l1">\n'
                                            in_list = True
                                        html_content += f'<li data-list-text="•"><p class="s2" style="padding-left: 23pt;text-indent: 0pt;line-height: 110%;text-align: left;">{bullet.strip()}</p></li>\n'
                                continue
                            else:
                                if in_list:
                                    html_content += '</ul>\n'
                                    # html_content += '<br>'
                                    in_list = False

                            if text in ["Patient Instructions", "Condition Overview", "Estado General","Instrucciones para el paciente", "Resumen de la condición"]:
                                if text in doc_type_tracking:
                                    continue
                                html_content += f'<h4>{text}</h4>\n'
                                doc_type_tracking += text
                                continue
                            
                            # Dataframe logic below
                            def fuzzy_match(text1, text2, threshold=89):
                                match_ratio = fuzz.ratio(normalize_whitespace(text1), normalize_whitespace(text2))
                                return match_ratio >= threshold
                            
                            def normalize_whitespace(text):
                                return re.sub(r'\s+', ' ', text).strip()
                            
                            # TEMPORARY FIX FOR THE WORD SPACE ISSUE IN THE FOOTER - WILL BE REMOVED ONCE A PERMANENT FIX IS FOUND
                            def in_line_space_remove(text):
                                text = re.sub(r'91\s*1', '911', text)
                                text = re.sub(r'G\s*O', 'GO', text)
                                text = re.sub(r'\s+', ' ', text)
                                return text
                            
                            # Logic Starts
                            if any(all(word in text.lower() for word in pattern) for pattern in emergency_line_match):
                                if text.count(".") > 0:
                                    text = text.split(".")[0] + "."
                                html_content += f"<p>{in_line_space_remove(text)}</p>"
                                continue
                           
                            filtered_df = self.grouped_df[
                                (self.grouped_df['page_num'] == page_num + 1) & 
                                (self.grouped_df['originalText'].apply(lambda x: fuzzy_match(x, text)))
                            ]

                            ######################## WAM-89 fixes starts ####################################################
                            # Check if filtered_df has more than one row, if so, select the first row
                            if self.one_pager_doc and len(filtered_df) > 1:
                                filtered_df = filtered_df.iloc[[0]]
                            ######################## WAM-89 fixes starts ####################################################

                            # Extract text from the filtered rows from the 'text' column that contains the text content with html tags
                            extracted_text = " ".join(filtered_df['text'].tolist())

                            # Remove "One Pager" and "One Page" from extracted_text if they exist
                            extracted_text = extracted_text.replace("One Pager", "").replace("One Page", "").replace("Una Pagina", "").replace("Un buscapersonas","").strip()
                            
                            # Remove duplicate title logic
                            original_text = filtered_df.iloc[0]['originalText'] if not filtered_df.empty else ""
                            if page_num > 0 and extracted_text.startswith('<h1') and not filtered_df.empty and fuzzy_match(original_text, title_header_text) and title_found:
                                continue

                            count += 1
                            if extracted_text and extracted_text.strip():  # Checks if it's not None and not empty after stripping
                                # Proceed with your logic using extracted_text
                                html_content += extracted_text
                            else:
                                html_content += f'<p>{text}</p>\n'
                            
                            # Remove duplicate title logic
                            if page_num == 0 and extracted_text.startswith('<h1') and not filtered_df.empty:
                                # Handle the case where title is header text is initially blank (i.e. if doc.metadata.get('title') is blank)
                                if not fuzzy_match(original_text, title_header_text):
                                    title_header_text = original_text  
                                title_found = True
                    
                    elif elem_type == 'image':
                        x0, y0, x1, y1 = coords
                        width = x1 - x0
                        height = y1 - y0
                        if width < 35 and height < 35:
                            html_content += f'<p style="text-indent: 0pt;text-align: left;"><span><img width="{width}" height="{height}" alt="image" src="{content}" style="float: left; margin-right: 10px;" /></span></p>\n'
                        else:
                            html_content += f'<p style="text-indent: 0pt;text-align: left;"><span><img width="{width}" height="{height}" alt="image" src="{content}" /></span></p>\n'
     
            # Ensure to close any open list at the end of processing
            if in_list:
                html_content += '</ul>\n'
                in_list = False

            html_content = self.replace_urls_with_hyperlinks(html_content)
            
            html_content = self.adjust_image_positions(html_content)
            html_content = self.confirm_subheadings(html_content)
            html_content = self.align_subheadings(html_content)
            html_content = self.adjust_images_in_bullets(html_content)
            html_content = self.merge_h1_tags(html_content)
            
            if removed_unwanted_text_flag == 'True' and not self.one_pager_doc:
                html_content =  self.remove_unwanted_text(html_content)
                
            html_content = self.remove_footer_image(html_content)

            #replace head content
            head_content = (
                '<head>'
                    '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
                    f'<title>{title}</title>'
                    f'<meta name="subject" content="{subject}"/>'
                    f'<meta name="author" content="{author}"/>'
                    f'<meta name="Keywords" content="{keywords}"/>'
                    f'<script type="text/javascript" src="{js_prepend}..\..\EpicVendorCommunication.js"></script>'
                    f'<link rel="stylesheet" href="{css_prepend}../../CSS/WEMytonomy.css">'
                '</head>'
            )

            body_start = html_content.find('<body>')

            # Check if <body> tag is found
            if body_start != -1:
                # Insert head_content before the <body> tag
                html_content = html_content[:body_start] + head_content + html_content[body_start:]

            #html_content = re.sub(head_pattern, r'\1' + head_content + r'\2', html_content, flags=re.DOTALL) 

            # Close the HTML tags
            html_content += """
            </body>
            </html>
            """

            with open(self.output_html_path, "w", encoding='utf-8') as file:
                file.write(html_content)
        except Exception as e:
            logger.error(f'Error in generate_html(): {e}')
            print(f'Error in generate_html(): {e}')
            raise  


if __name__ == "__main__":
    logger = init_logging('LOGGING_PDFToHtmlConverter', 'PDFToHtmlConverter')

    filecount = 0

    pdf_file_path = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/DownloadedPDFs' ).replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','') 
    html_file_path = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/HTML').replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','')
    output_images_dir = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/HTML/Images').replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','')

    # Check if the HTML output directory exists and is not empty
    if os.path.exists(html_file_path):
        # If the directory exists and is not empty, delete its contents
        for root, dirs, files in os.walk(html_file_path):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))
                
    # Make the HTML/Images directory if it doesn't exist
    os.makedirs(output_images_dir, exist_ok=True)

    # Process each pdf file
    for dirpath, dirnames, filenames in os.walk(pdf_file_path):
        # Maintain the same relative folder structure within html_file_path as in pdf_file_path
        relative_dir_path = os.path.relpath(dirpath, pdf_file_path)
        output_html_dir = os.path.join(html_file_path, relative_dir_path).replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','')
        
        os.makedirs(output_html_dir, exist_ok=True)

        for filename in filenames:
            if filename.endswith('.pdf'):

                pdf_path = os.path.join(dirpath,filename)
                html_name = os.path.splitext(filename)[0] + '.html'
            

                output_html_path = os.path.join(output_html_dir, html_name)
                output_html_path = output_html_path.replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','')
                # Main method call
                logger.info(f'DOING HTML PATH: {output_html_path}')
                # setting a variable to keep track of whether the document that is currently processing is a one pager or not
                one_pager_doc = False
                if filename[:2] == '1P':
                    one_pager_doc = True
               #POC Change
                grouped_df = process_pdf_to_html(pdf_path)
                converter = MytonomyPDFConverter(pdf_path, output_html_path, one_pager_doc, grouped_df=grouped_df )
                #converter = MytonomyPDFConverter(pdf_path, output_html_path)
                #POC Change
                try:
                    converter.generate_html()
                except Exception as e:
                    logger.error("Error generating HTML. Terminating")
                    sys.exit(1)
                filecount += 1
    
    # Debugging
    print("Number of files converted is: " + str(filecount))
    for i in text_removed:
        print(f'{i}')
