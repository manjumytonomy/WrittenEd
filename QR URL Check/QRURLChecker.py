import os
import fitz  # PyMuPDF
import re
import numpy as np
import cv2
from pdf2image import convert_from_path
from PIL import Image
from collections import defaultdict
import configparser
import logging
import sys
import pandas as pd

'''
File checks all PDFs and notes all files with matching QR codes and URLs. Use this to see if files have the wrong QR code or URL.
'''

config = configparser.ConfigParser()
config.read('../config.ini')

customer = config['CUSTOMER']['customer_name']
configCustomer = configparser.ConfigParser()
configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

# Set up logging
log_file = os.path.join(project_dir, config['LOGGING']['log_file'])
logging.basicConfig(filename=log_file, level=config['LOGGING']['log_level'], format='%(asctime)s - %(levelname)s - %(message)s')

class PDFProcessor:
    def __init__(self, pdf_directory):
        self.pdf_directory = pdf_directory
        logging.info(f"**********Source PDF Directory for QRURLChecker : {self.pdf_directory} ")
        self.url_map = defaultdict(list)
        self.qr_code_map = defaultdict(list)
        self.page_count = 0
        self.results = []

    def clean_url(self, url):
        # Replace soft hyphen with dash
        url = url.replace('\xad', '-')
        # Remove newline characters
        url = url.replace('\n', '')
        # Use regex to extract only the URL part
        match = re.search(r'https?://myto\.us/p[-\w]*', url)
        return match.group(0) if match else None

    def extract_urls(self, text):
        # Regular expression to match URLs including optional soft hyphens and spaces
        url_pattern = re.compile(r'https?://myto\.us/p[-\w\s\xad]*')
        urls = url_pattern.findall(text)
        
        # Clean and normalize URLs
        cleaned_urls = [self.clean_url(url) for url in urls]
        
        # Remove duplicates and filter out None values
        cleaned_urls = list(filter(None, cleaned_urls))
        
        return cleaned_urls

    def extract_text_from_pdf(self, pdf_path):
        pdf_document = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        return text

    def extract_qr_code(self, image):
        # Convert PIL image to OpenCV format
        open_cv_image = np.array(image)
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
        
        # Create QRCodeDetector object
        detector = cv2.QRCodeDetector()
        
        # Use detectAndDecode method to detect and decode QR codes
        qr_code, _, _ = detector.detectAndDecode(open_cv_image)
        
        #if qr_code:
        #     print(f"Detected QR Code: {qr_code}")
        
        return qr_code

    def process_pdfs(self):
        try:
            logging.info(f"**********PDF Directory is {self.pdf_directory} ")
            for root, dirs, files in os.walk(self.pdf_directory):
                for filename in files:
                    if filename.endswith('.pdf'):
                        logging.debug(f"**************File is {filename}")
                        pdf_path = os.path.join(root, filename)
                        self.page_count += 1
                        
                        # Extract text from the PDF
                        text = self.extract_text_from_pdf(pdf_path)
                        
                        # Extract URLs from the text
                        urls = self.extract_urls(text)
                        logging.debug(f'urls: {urls}')
                        
                        # Assume the first URL is the broadcast URL
                        broadcast_url = urls[0] if urls else None
                        
                        # Convert PDF to images
                        images = convert_from_path(pdf_path, dpi=300)
                        
                        qr_code = None
                        for i, image in enumerate(images):
                            # Extract QR codes from the image
                            qr_code = self.extract_qr_code(image)
                            if qr_code:
                                break
                        
                        # Determine if URLs and QR codes are the same
                        both_urls_same = (broadcast_url == qr_code)
                        
                        # Append results
                        self.results.append({
                            'File Path': pdf_path,
                            'Missing QR Code': '' if qr_code else 'Yes',
                            'Missing Broadcast URL': '' if broadcast_url else 'Yes',
                            'QR Code': qr_code,
                            'Broadcast URL': broadcast_url,
                            'Both URLs the Same': both_urls_same
                        })
                        
                        # Store filename with QR code
                        if qr_code:
                            self.qr_code_map[qr_code].append(pdf_path)

        except Exception as e:
            logging.error(f"Error checking URL and QR codes in PDF: {e}")
            raise

    def print_duplicates(self):
        # Find and print duplicates for URLs
        logging.info("***************************************Identifying Duplicate URLs***************************************")
        for url, files in self.url_map.items():
            if len(files) > 1:
                logging.info(f"URL: {url}")
                logging.info("Files with this URL:")
                for file in files:
                    logging.info(f"  {file}")

        # Find and print duplicates for QR codes
        logging.info("\n***************************************Identifying Duplicate QR Codes***************************************")
        for qr_code, files in self.qr_code_map.items():
            if len(files) > 1:
                logging.info(f"QR Code: {qr_code}")
                logging.info("Files with this QR Code:")
                for file in files:
                    logging.info(f"  {file}")

        logging.info(f'Total files checked in QRURLChecker: {self.page_count}')

    def save_results_to_excel(self):
        # Convert results to DataFrame
        df = pd.DataFrame(self.results)
        
        # Define the specific output file path
        output_dir = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage')
        output_file = os.path.join(output_dir, 'pdf_analysis_results.xlsx')
        
        # Delete the file if it already exists
        if os.path.exists(output_file):
            os.remove(output_file)
        
        # Save DataFrame to Excel
        df.to_excel(output_file, index=False, engine='openpyxl')
        logging.info(f"Results saved to {output_file}")

pdf_processor = PDFProcessor(os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/DownloadedPDFs'))
try:
    pdf_processor.process_pdfs()
except Exception as e:
    logging.error(f"Error in QRURLChecker. Terminating {e}")
    sys.exit(1)
pdf_processor.print_duplicates()
pdf_processor.save_results_to_excel()
