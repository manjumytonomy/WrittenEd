import fitz
import os
from unidecode import unidecode
import html
import logging
import configparser
import sys

removed_text = []

config = configparser.ConfigParser()
config.read('../config.ini')


script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

# Set up logging
log_file = os.path.join(project_dir, config['LOGGING']['log_file'])
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

header_text = ""
document_count = 0

def replace_special_characters(text):
    replacements = {
        '': '•',  # Bullet point
        '&': '&amp;',
        '"': '&quot;',
        "'": '&#39;',  # Apostrophe
        '&#39;' : "'",
        '\u00AD' : '-',  # Soft hyphen
        '­': '-',  # Soft hyphen
        '●': '•'
        # Add other replacements as needed
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text

def unwanted_text(text):
    strings_to_remove = ["Where Can You Learn More?", "[Health system standard for contact]", 
                            "[Health system standard disclaimer for written materials.]",
                            "Watch the video by using your phone camera to click on the QR Code above."
                            "Información de contacto estándar del sistema de salud",
                            "Dónde puede obtener más información",
                            "Vea el video utilizando la cámara de su teléfono para darle clic a el código QR de arriba.",
                            "@1@ Mytonomy @®"]
    
    if text in strings_to_remove:
        return True 
    elif "o" == text or '~' in text or ',.' in text or \
                                    '.,' in text or '>' in text or '<' in text or '-.' in text or (('00' in text) and ('100' not in text)) \
                                        or ":'" in text or 'r:' in text or '(!' in text or '---' in text or '--' in text or 'lnova™' in text \
                                        or '□' in text or '®' in text or '@1@' in text or '[!!' in text or 'l @Mytonomy' in text \
                                        or '[Health system standard disclaimer for written materials.]' in text \
                                        or 'l i Mytonomy' in text  or '@1@ Mytonomy @ !ID' in text or '@® M\1tonomy @ \'1' in text \
                                        or '1!1@ Mytonomy @100' in text or '@1@ Mytonomy @' in text or 'l!I@ Mytonomy @(,!)' in text \
                                        or '@® M,,tonomy @ ,,' in text or 'Mytonomy' in text :
        return True
    else:
        return False 

def is_within_bbox(text_bbox, image_bbox):
        """
        Check if the text bounding box overlaps with or is within the image bounding box, allowing for an offset range.
        """
        tx0, ty0, tx1, ty1 = text_bbox
        ix0, iy0, ix1, iy1 = image_bbox

        ix0 -= 10
        iy0 -= 10
        ix1 += 10
        iy1 += 10

        # Check if the text bounding box is within or overlapping with the adjusted image bounding box
        return (tx0 >= ix0 and ty0 >= iy0 and tx1 <= ix1 and ty1 <= iy1)

def extract_text_with_positions(page, page_num, images_info, pdf_path):
    try:
        #print(f'images info in extract_with_positions: {images_info}')
        global document_count
        document_count += 1
        divided_blocks = []
        #blocks = page.get_text("blocks")
        blocks = page.get_text("blocks", flags = 1+2+8)
        bullet_list = []
        bullet_text = ""
        bullet_alignment = 0
        VERTICAL_THRESHOLD = 3
        page_width = page.rect.width
        for block in blocks:

            if len(block) >= 5:
                bbox = block[:4]
                #text = block[4].strip()
                text = block[4].strip().replace('\n', '').replace('\r', '')  # Strip new line characters
                props = block[5:]  # Additional properties
                text = replace_special_characters(text)
                # Removing text that is within bounding box of an image - removes all text extracted from imgs
                if any(is_within_bbox(bbox, image_info[1]) for i, image_info in enumerate(images_info)):
                    #print(f'this text: {text} is within bbox')
                    removed_text.append(f"removed text in file {pdf_path}: {text}")
                    continue
                if unwanted_text(text):
                    continue
                if len(text.strip()) == 0:
                    continue
                # logic to handle processing of text that contains bullet points within the source pdf
                elif len(bullet_text) != 0:
                    #checks to see if the next block is indented, and if its indented its considered the text within the same bullet point
                    if (bbox[0] > bullet_alignment) and ((bbox[1] - bullet_y) < VERTICAL_THRESHOLD) and is_left_aligned(block, page_width):
                        bullet_text += " "+ text
                        bullet_y = bbox[3]
                        continue
                    #checks for the next bullet point in the bullet list in the source pdf
                    elif text.startswith('•') or text.startswith('&#8226;') or text.startswith('•'):
                        bullet_text += text
                        bullet_alignment = bbox[0]
                        bullet_y = bbox[3]
                        continue
                    else:
                        divided_blocks.append((*bullet_bbox, bullet_text, *bullet_props))
                        bullet_text = ""
                        # If text isn't apart of bullet text, it will add current text as separate block below bullet list
                        divided_blocks.append((*bbox, text, *props ))
                        continue
                elif text.startswith('•') or text.startswith('&#8226;'):
                    bullet_text += text
                    bullet_bbox = bbox
                    bullet_props = props
                    bullet_alignment = bbox[0]
                    bullet_y = bbox[3]
                    continue
                #if the text does not contain bullet points then it continues
                else:
                    divided_blocks.append((*bbox, text, *props))
       
        # After all blocks are processed, add any remaining bullet text
        if len(bullet_text) > 0:
            divided_blocks.append((*bullet_bbox, bullet_text, *bullet_props))

        divided_blocks = handle_repeated_titles(divided_blocks, page_num, page_width)

        divided_blocks = merge_paragraphs(divided_blocks, page_width)
       
        return divided_blocks, removed_text
    except Exception as e:
        logging.error(f"Error detected in extracting text with positions: {e}")
        sys.exit(1)



def is_left_aligned(block, page_width, alignment_threshold=0.1):
    x1 = block[2]
    x0 = block[0]
    if x0 < page_width*(1/4):
        return True
    return False

# Handle text wrapping within a paragraph
def merge_paragraphs(divided_blocks, page_width, merge_threshold=2, alignment_threshold=20):
   # print(f'divided blocks after titles handled: {divided_blocks}')
    merged_blocks = []
    i = 0
    while i < len(divided_blocks):
        current_block = divided_blocks[i]
        current_bbox = list(current_block[:4])  # Convert to list to modify bbox
        current_text = current_block[4]
        current_props = current_block[5:]
        alignment = "left"
        

        # Check if the current block is left-aligned
        if not is_left_aligned(current_block, page_width, alignment_threshold):
            alignment = "right"
            merged_blocks.append((*current_bbox, current_text, *current_props, alignment))
            i += 1
            continue

        # Check if the next block should be merged
        while i + 1 < len(divided_blocks):
            next_block = divided_blocks[i + 1]
            next_bbox = next_block[:4]
            next_text = next_block[4]
            next_props = next_block[5:]
            next_alignment = "left"

            if not is_left_aligned(next_block, page_width, alignment_threshold):
                next_alignment = "right"
                
            if abs(current_bbox[3] - next_bbox[1]) < merge_threshold and (alignment == next_alignment):
                # Merge the current block with the next block
                current_text += " " + next_text
                current_bbox[3] = next_bbox[3]  # Update the bottom y-coordinate
                i += 1
            else:
                break
        merged_blocks.append((*current_bbox, current_text, *current_props, alignment))

        i += 1

    return merged_blocks


# Process title elimination in subpages
def handle_repeated_titles(divided_blocks, page_num, page_width):
    removed_texts = []
    # Remove elements where blocks[4] (text) is empty
    divided_blocks = [block for block in divided_blocks if block[4] != '']
    
    # Sort divided_blocks by the y-coordinate of the bounding box in ascending order
    divided_blocks.sort(key=lambda b: b[1])
    #print(f'divided blocks after empty text removal: {divided_blocks}')
    
    if (page_num >= 1):
        if len(divided_blocks) > 0:
            first_block_x2 = divided_blocks[0][2] # Accessing the blocks[2] value of the first element (title)
            first_block_x1 = divided_blocks[0][0] 
            
            # Gets x coordinate of first text element, goes through elements until first left-aligned text element is found - deletes all 
            # text elements before (Deletes title)
            for i in range(1, len(divided_blocks)):
                # Making sure the right x coordinate of the bounding box of the text is within the same range as the bounding box of the title
                # Makes sure the text is a part of the title by checking if the right x coordinate of the bounding box is in the same range
                # divided_blocks[i][0] < first_block_x1*(1/4) Makes sure the text is not deleted if it is left aligned but still stretches to the end of the page
                if (is_left_aligned(divided_blocks[i], page_width)):

                    divided_blocks = divided_blocks[i:]
                    #print(f'after deletion: {divided_blocks}')
                    break
                else:
                    removed_texts.append(divided_blocks[i][4])

        
        # Print all removed text
        if removed_texts:
            print(f"Text removed from handle_repeated_titles function: {', '.join(removed_texts)}")
    return divided_blocks

def is_part_of_title(block_text, title):
    if block_text in title:
        return True 
    return False 

def is_heading(block_text):
    if isinstance(block_text, dict) and 'lines' in block_text:
        for line in block_text['lines']:
            for span in line['spans']:
                span_font = span['font']
                if "bold" in span_font.lower():
                    return True
    return False

# Remove all whitespace and compare purely the text
def clean_text(text):
    return re.sub(r'\s+', '', text)  # Remove all whitespace characters


def is_bbox_match(bbox1, bbox2, threshold=0.5, epsilon=1e-5):
    """
    Compare two bounding boxes (bbox1 and bbox2). Return True if they match within a given threshold,
    or if one bounding box is contained within the other, allowing for a small threshold.
    """
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2

    # Check if the bounding boxes overlap within the given threshold
    if (
        abs(x0_1 - x0_2) <= threshold + epsilon and
        abs(y0_1 - y0_2) <= threshold + epsilon and
        abs(x1_1 - x1_2) <= threshold + epsilon and
        abs(y1_1 - y1_2) <= threshold + epsilon
    ):
        return True

    if (abs(x0_1 - x0_2) <= threshold) and (abs(y0_1 - y0_2) <= threshold):
        return True

    return False

def is_text_match(text1, text2):
    if text1 == text2:
        return True
    if text1 in text2:
        return True
    if text2 in text1:
        return True
    
    return False 

def extract_text_properties(pdf_path, block_text, block_coords):
    try:
        '''This function extracts text properties such as font size, color, weight, and bounding box information.'''
        previous_text = []

        global document_count
        global header_text

        if document_count == 1:
            header_text = ""
            document_count = 0

        # Open the PDF
        document = fitz.open(pdf_path)
        for page_num in range(len(document)):
            page = document.load_page(page_num)

            #blocks = page.get_text("dict")["blocks"]
            blocks=page.get_text("dict", flags = 1+2+8)["blocks"]
            for block in blocks:
                if block['type'] == 0:  # Text block
                    for line in block['lines']:
                        for span in line['spans']:
                            text = replace_special_characters(span["text"])
                            if not text:
                                continue

                            font_size = span["size"]
                            font_name = span["font"]
                            color = span["color"]
                            if 'Bold' in font_name:
                                font_weight = '700'
                            else:
                                font_weight = 'normal'

                            # The bounding box for the current span (text block)
                            bbox = span['bbox'] if 'bbox' in span else None

                            # Compare the bounding box of the current block with the one passed in
                            if bbox and block_coords:
                                if is_bbox_match(bbox, block_coords) and is_text_match(text, block_text):
                                    return {"font_size": font_size, "font_weight": font_weight, "font_color": '#000000'}

        return None
    except Exception as e:
        logging.error(f"Error detected in extracting text properties: {e}")
        sys.exit(1)


