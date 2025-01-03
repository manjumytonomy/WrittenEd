import fitz
import os
from unidecode import unidecode
import html
import logging
import configparser
import sys
import re 

removed_text = []
header_text = ""
document_count = 0

def remove_invalid_text(text):
    
    if "o" == text or '~' in text or ',.' in text or \
                                    '.,' in text or '>' in text or '<' in text or '-.' in text or (('00' in text) and ('100' not in text)) \
                                        or ":'" in text or 'r:' in text or '(!' in text or '---' in text or '--' in text or 'lnova™' in text \
                                        or '□' in text or '®' in text or '@1@' in text or '[!!' in text or 'l @Mytonomy' in text \
                                        or '[Health system standard disclaimer for written materials.]' in text \
                                        or 'l i Mytonomy' in text  or '@1@ Mytonomy @ !ID' in text or '@® M\1tonomy @ \'1' in text \
                                        or '1!1@ Mytonomy @100' in text or '@1@ Mytonomy @' in text or 'l!I@ Mytonomy @(,!)' in text \
                                        or '@® M,,tonomy @ ,,' in text or 'Mytonomy' in text or "" "'  ... " in text \
                                        or "c.rm -" in text or "I .. __ =-_...._..;" in text or 'ClrCI  L:.1...ft.!  Cl~C' in text \
                                        or "&quot;&quot;' ..." in text:
        return True
    else:
        return False 
    
def is_all_numbers(input_string):
    return input_string.isdigit()

def replace_special_characters(text):
    replacements = {
        '': '•',  # Bullet point
        '&': '&amp;',
        '"': '&quot;',
        "'": '&#39;',  # Apostrophe
        '&#39;' : "'",
        '\u00AD' : '-',  # Soft hyphen
        '­': '-',  # Soft hyphen
        '●': '•',
        ':': ''
        # Add other replacements as needed
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text

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

def one_pager_extract_text_with_positions(page, page_num, images_info, pdf_path):
    try:
        global document_count
        global header_text
        document_count += 1
        divided_blocks = []
        doc = fitz.open(pdf_path)
        #blocks = page.get_text("blocks")
        blocks = page.get_text("blocks", flags = 1+2+8)
        print("THIS IS REAL OG")
        # Pre-process blocks to split "One Pager" into separate blocks
        preprocessed_blocks = []
        for block in blocks:
            if len(block) >= 5:
                bbox = block[:4]
                text = block[4].strip().replace('\n', '').replace('\r', '')
                props = block[5:]  # Additional properties
                text = replace_special_characters(text)
                # # Check for "One Pager" in the text
                # if "One Pager" in text:
                #     # Split the text after "One Pager"
                #     one_pager_text = "One Pager"
                #     rest_of_text = text.split("One Pager", 1)[1].strip()
                #     # Add two blocks: one for "One Pager" and one for the rest
                #     preprocessed_blocks.append((*bbox, one_pager_text, *props))
                #     if rest_of_text:
                #         preprocessed_blocks.append((*bbox, rest_of_text, *props))
                #         header_text += rest_of_text
                # Check if the text contains "One Pager", "One Page", or "Una Pagina"
                if "One Pager" in text or "One Page" in text or "Una Página" in text or "Un buscapersonas" in text:
                    # Determine which keyword is present and use it to split the text
                    if "One Pager" in text:
                        keyword = "One Pager"
                    elif "One Page" in text:
                        keyword = "One Page"
                    elif "Un buscapersonas" in text:
                        keyword = "Un buscapersonas"
                    else:
                        keyword = "Una Página"
                    
                    # Split the text after the identified keyword
                    keyword_text = keyword
                    rest_of_text = text.split(keyword, 1)[1].strip()
                    
                    # Add two blocks: one for the keyword and one for the rest
                    preprocessed_blocks.append((*bbox, keyword_text, *props))
                    if rest_of_text:
                        preprocessed_blocks.append((*bbox, rest_of_text, *props))
                        header_text += rest_of_text
                else:
                    preprocessed_blocks.append(block)

        for i in preprocessed_blocks:
            print(i)
        bullet_list = []
        bullet_text = ""
        bullet_alignment = 0
        VERTICAL_THRESHOLD = 3
        page_width = page.rect.width
        for block in preprocessed_blocks:
            if len(block) >= 5:
                bbox = block[:4]
                #text = block[4].strip()
                text = block[4].strip().replace('\n', '').replace('\r', '')  # Strip new line characters
                props = block[5:]  # Additional properties
                text = replace_special_characters(text)
                # this is for the one pager
                if "One Pager" in text or "One Page" in text or "Una Página" in text or "Un buscapersonas" in text:
                    continue
                # this is for the one pager
                '''
                if "One Pager" in text:
                    # Split the text into two parts: one with "One Pager" and one with the rest
                    one_pager_text = "One Pager"
                    rest_of_text = text.split("One Pager", 1)[1].strip()
                    # Create two blocks: one for "One Pager" and one for the remaining text
                    divided_blocks.append((*bbox, one_pager_text, *props))  # Block for "One Pager"
                    
                    # You can adjust the bounding box for the remaining text if needed
                    divided_blocks.append((*bbox, rest_of_text, *props))  # Block for the remaining text
                if "One Pager" in text:
                    continue
                '''
                # this is for the one pager
                if "P a g e" in text or "Pági na" in text or "1P" in text or "Alta ES" in text:
                    continue
                # Removing text that is within bounding box of an image - removes all text extracted from imgs
                if any(is_within_bbox(bbox, image_info[1]) for i, image_info in enumerate(images_info)):
                    #print(f'this text: {text} is within bbox')
                    removed_text.append(f"removed text in file {pdf_path}: {text}")
                    continue
                if remove_invalid_text(text):
                    continue
                if is_all_numbers(text):
                    continue
                if len(text.strip()) == 0:
                    continue
                # logic to handle processing of text that contains bullet points within the source pdf
                ##################################### Fix for WAM-92 Starts ########################################
                elif len(bullet_text) != 0:
                    #checks to see if the next block is indented, and if its indented its considered the text within the same bullet point
                    if (bbox[0] > bullet_alignment) and ((bbox[1] - bullet_y) < VERTICAL_THRESHOLD) and is_left_aligned(block, page_width):
                        bullet_text += " " + text
                        bullet_y = bbox[3]
                        continue
                    #checks for the next bullet point in the bullet list in the source pdf
                    elif text.startswith('•') or text.startswith('&#8226;') or re.match(r'^\d+[.)]', text):
                        bullet_text += text
                        bullet_alignment = bbox[0]
                        bullet_y = bbox[3]
                        continue
                    else:
                        if re.match(r'^\d+[.)]', bullet_text) and re.search(r'\d+\.\s', bullet_text[1:]):
                            formatted_bullet_text = split_numbered_bullets(bullet_text)
                        else:
                            formatted_bullet_text = bullet_text
                        # Append to divided_blocks with formatting as needed
                        divided_blocks.append((*bullet_bbox, formatted_bullet_text, *bullet_props))
                        bullet_text = ""
                        # If text isn't apart of bullet text, it will add current text as separate block below bullet list
                        divided_blocks.append((*bbox, text, *props))
                        continue
                elif text.startswith('•') or text.startswith('&#8226;') or re.match(r'^\d+[.)]', text):
                    bullet_text += text
                    bullet_bbox = bbox
                    bullet_props = props
                    bullet_alignment = bbox[0]
                    bullet_y = bbox[3]
                    continue
                #if the text does not contain bullet points then it continues
                else:
                    divided_blocks.append((*bbox, text, *props))
                ##################################### Fix for WAM-92 Ends ########################################
        
        # After all blocks are processed, add any remaining bullet text
        if len(bullet_text) > 0:
            divided_blocks.append((*bullet_bbox, bullet_text, *bullet_props))
        print(f"THIS IS DIVIDED BLOCKS {page_num}")
        for i in divided_blocks:
            print(i)
        divided_blocks = handle_repeated_titles(divided_blocks, page_num, page_width) 
        print(f"THIS IS AFTER HANDLE REPEATED TITLES {page_num}")
        for i in divided_blocks:
            print(i)

        divided_blocks = handle_footer_cleanup(divided_blocks, page_num, doc)
        print(f"THIS IS AFTER HANDLE FOOTER CLEANUP {page_num}")
        for i in divided_blocks:
            print(i)

        divided_blocks = merge_paragraphs(divided_blocks, page_width)
        print(f"THIS IS AFTER MERGE PARAGRAPHS {page_num}")
        for i in divided_blocks:
            print(i)
        
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
                    print(f"INSIDE THE LEFT-ALIGNED CONDITION: Block {i} is left-aligned: {divided_blocks[i]}")
                    divided_blocks = divided_blocks[i:]
                    #print(f'after deletion: {divided_blocks}')
                    break
                else:
                    removed_texts.append(divided_blocks[i][4])
        
        # Print all removed text
        if removed_texts:
            print(f"Text removed from handle_repeated_titles function: {', '.join(removed_texts)}")
    return divided_blocks

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

def one_pager_extract_text_properties(pdf_path, block_text, block_coords):
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
            blocks = page.get_text("dict", flags = 1+2+8)["blocks"]
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


##################################### Fix for WAM-92 Starts ########################################
def split_numbered_bullets(text):
    bullets = re.sub(r'(\d+)\.', r'<p>\1. ', text).strip()
    return bullets
##################################### Fix for WAM-92 Ends ########################################

def handle_footer_cleanup(divided_blocks, page_num, doc):
    pattern1e = ["watch the video", "learn more about"]
    pattern2e = ["learn more about", "visit", "link"]
    pattern3e = ["learn more about", "go to", "link"]
    pattern4e = ["(insert link)"]
    pattern5e = ["corner", "link", "web browser"]
    pattern6e = ["qr code", "link"]
    pattern7e = ["enterthe qrcode"]
    pattern8e = ["phone camera", "qr code"]
    pattern9e = ["have questions", "medical help"]
    pattern10e = ["| p a ge"]
    pattern11e = ["page |"]
    pattern12e = ["system standard for contact"]
    pattern13e = ["system standard disclaimer"]
    pattern14e = ["healthy heart 041023"]
    pattern15e = ["updated 081522"]
    pattern16e = ["updated 08092022"]
    pattern17e = ["where can you learn more"]
    
    extra_pattern1e = ["code", "url"]
    extra_pattern2e = ["between levels 5 to 7"]
    
    english_patterns = [pattern1e, pattern2e, pattern3e, pattern4e, pattern5e, pattern6e, pattern7e, pattern8e, pattern9e, pattern10e, 
                        pattern11e, pattern12e, pattern13e, pattern14e, pattern15e, pattern16e, pattern17e]
    english_patterns2 = [extra_pattern1e, extra_pattern2e]
    
    pattern1s = ["vea el video", "más información sobre"]
    pattern2s = ["vea el video utilizando", "qr de arriba"]
    pattern3s = ["dónde puede obtener más información"]
    pattern4s = ["dónde puedes obtener más información"]
    pattern5s = ["más información sobre", "visite [enlace]"]
    pattern6s = ["más información sobre", "vaya a [link]"]
    pattern7s = ["más informaciān sobre", "vea el video"]
    pattern8s = ["más información sobre", "mira el video"]
    pattern9s = ["teléfono al código qr"]
    pattern10s = ["url", "código qr"]
    pattern11s = ["navegador web", "código qr"]
    pattern12s = ["código qr", "navegador"]
    pattern13s = ["código qr", "escribe este enlace"]
    pattern14s = ["pági na |"]
    pattern15s = ["página |"]
    pattern16s = ["estándar del sistema de salud)"]
    pattern17s = ["descargo de responsabilidad estándar"]
    pattern18s = ["sistema sanitario estándar de contacto"]
    pattern19s = ["es 040723"]
    pattern20s = ["alfabetización sanitaria entre los niveles 5 y 7"]
    pattern21s = ["alfabetización en salu d entre los niveles 5 a 7"]
    pattern22s = ["asistencia médica", "con nosotros"]
    
    spanish_patterns = [pattern1s, pattern2s, pattern3s, pattern4s, pattern5s, pattern6s, pattern7s, pattern8s, pattern9s, pattern10s, 
                        pattern11s, pattern12s, pattern13s, pattern14s, pattern15s, pattern16s, pattern17s, pattern18s, pattern19s, pattern20s, 
                        pattern21s, pattern22s]
    
    intermediate_page_patterns = [["| p a ge"], ["page |"], ["pági na |"], ["página |"], 
                                  ["healthy heart 041023"], ["updated 081522"], ["updated 08092022"], ["es 040723"]]
    
    match_patterns = ["-"]
    
    num_blocks = len(divided_blocks)
    last_few_block_idxs = [num_blocks-5, num_blocks-4, num_blocks-3, num_blocks-2, num_blocks-1]
    remove_indices = []
    
    if page_num not in [len(doc)-2, len(doc)-1]:
        for idx, block in enumerate(divided_blocks):
            text = re.sub(r'\s+', ' ', block[4].strip().lower())
            for pattern_list in intermediate_page_patterns:
                if all(pattern in text for pattern in pattern_list):
                    remove_indices.append(idx)
                    break
        return [block for idx, block in enumerate(divided_blocks) if idx not in remove_indices]
    
    for idx, block in enumerate(divided_blocks):
        text = re.sub(r'\s+', ' ', block[4].strip().lower())
        idx_removed = False
        
        if "if you have a medical emergency" in text and text.count(".") > 1:
            new_text = block[4].split(".", 1)[0].strip() + "."
            bbox = block[:4]
            current_props = block[5:]
            divided_blocks[idx] = (*bbox, new_text, *current_props)
            continue
        
        for pattern_list in english_patterns:
            if all(pattern in text for pattern in pattern_list):
                remove_indices.append(idx)
                idx_removed = True
                break
        
        if idx_removed:
            continue    
        
        for pattern_list in english_patterns2:
            if all(pattern in text for pattern in pattern_list) and idx in last_few_block_idxs:
                remove_indices.append(idx)
                idx_removed = True
                break
        
        if idx_removed:
            continue   
        
        if "si tienes una emergencia" in text and text.count(".") > 1:
            bbox = list(block[:4])  # Convert to list to modify bbox
            new_text = block[4].split(".")[0] + "."
            current_props = block[5:]
            divided_blocks[idx] = (*bbox, new_text, *current_props)
            continue
            
        for pattern_list in spanish_patterns:
            if all(pattern in text for pattern in pattern_list):
                remove_indices.append(idx)
                break
            
        if any(text == pattern for pattern in match_patterns):
            remove_indices.append(idx)
            continue
            
    return [block for idx, block in enumerate(divided_blocks) if idx not in remove_indices]
