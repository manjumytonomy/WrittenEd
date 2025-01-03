import fitz  # PyMuPDF
from unidecode import unidecode
import pandas as pd
import re
import numpy as np

def process_pdf_to_html(path):
    # Open the PDF document
    doc = fitz.open(path)

    # Extract text blocks and process them
    output = []
    for page in doc:
        output += page.get_text("blocks", flags = 1+2+8)

    previous_block_id = 0
    plain_text_list = []

    # Extract and clean text using Unidecode
    for block in output:
        if block[6] == 0:  # Only take the text
            if previous_block_id != block[5]:  # Compare block number
                print("\n")
            plain_text = unidecode(block[4])
            print(plain_text)
            plain_text_list.append(plain_text)

    # Store the text in a DataFrame for NLP tasks
    df = pd.DataFrame(plain_text_list, columns=['text'])

    # Span extraction for deeper text analysis
    block_dict = {}
    page_num = 1

    # Create a block dictionary for each page
    for page in doc:
        file_dict = page.get_text('dict', flags = 1+2+8)
        blocks = file_dict['blocks']
        block_dict[page_num] = blocks
        page_num += 1

    # Create an empty DataFrame for spans
    spans = pd.DataFrame(columns=['page_num','block_id', 'xmin', 'ymin', 'xmax', 'ymax', 'text', 'is_upper', 'is_bold', 'span_font', 'font_size'])

    # Iterate over blocks, lines, and spans
    rows = []
    for page_num, blocks in block_dict.items():
        for block in blocks:
            if block['type'] == 0:  # Only text blocks
                block_id = block['number'] 
                for line in block['lines']:
                    for span in line['spans']:
                        xmin, ymin, xmax, ymax = list(span['bbox'])
                        font_size = span['size']
                        text = unidecode(span['text'])
                        span_font = span['font']

                        is_upper = False
                        is_bold = False

                        if "bold" in span_font.lower():
                            is_bold = True
                        if re.sub("[\(\[].*?[\)\]]", "", text).isupper():
                            is_upper = True

                        if text.replace(" ", "") != "":
                            rows.append((page_num, block_id, xmin, ymin, xmax, ymax, text, is_upper, is_bold, span_font, font_size))

    span_df = pd.DataFrame(rows, columns=['page_num', 'block_id', 'xmin', 'ymin', 'xmax', 'ymax', 'text', 'is_upper', 'is_bold', 'span_font', 'font_size'])
    
    # Determine 'p' (paragraph) size based on text style frequencies
    span_scores = []
    special = '[(_:/,#%\=@)]'

    for index, span_row in span_df.iterrows():
        score = round(span_row.font_size)
        text = span_row.text

        if not re.search(special, text):
            if span_row.is_bold:
                score += 1
            if span_row.is_upper:
                score += 1
        span_scores.append(score)

    values, counts = np.unique(span_scores, return_counts=True)
    style_dict = {value: count for value, count in zip(values, counts)}

    p_size = max(style_dict, key=style_dict.get)

    # Assign tags to different text styles
    tag = {}
    idx = 0

    for size in sorted(values, reverse=True):
        idx += 1
        if size == p_size:
            idx = 0
            tag[size] = 'p'
        elif size > p_size:
            tag[size] = f'h{idx}'
        else:
            tag[size] = f's{idx}'

    span_tags = [tag[score] for score in span_scores]
    span_df['tag'] = span_tags

    # Step 5: Group by block_id and concatenate HTML-formatted text
    rows_with_html = []
    for page_num, blocks in block_dict.items():
        for block in blocks:
            if block['type'] == 0:  # Only text blocks
                block_id = block['number']
                block_text = []  # Collect text for this block
                original_text = []
                tag_for_text = ''
                for line in block['lines']:
                    for span in line['spans']:
                        xmin, ymin, xmax, ymax = list(span['bbox'])
                        font_size = span['size']
                        text = span['text']
                        span_font = span['font']
                        color = span["color"]

                        is_upper = "uppercase" in span_font.lower()
                        is_bold = "bold" in span_font.lower()

                        # Validate and format color value
                        if isinstance(color, int):
                            font_color = f'#{color:06x}'  # Ensure it's a 6-digit hex
                        elif isinstance(color, tuple) and len(color) >= 3:
                            font_color = f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}'
                        else:
                            font_color = '#000000'  # Fallback to black if invalid
                        # Validate color length (should be 7 characters including #)
                        if len(font_color) != 7 or not font_color.startswith('#'):
                            font_color = '#000000'  # Fallback to black if invalid

                        if text.strip():  # Skip empty text
                            original_text.append(text)
                            text = unidecode(text)

                        # Determine the appropriate tag
                        if font_size > 18:
                            tag_for_text = 'h1'
                        elif font_size > 16:
                            tag_for_text = 'h2'
                        else:
                            tag_for_text = 'p'

                        # Apply bold if necessary
                        if is_bold:
                            text = f"<b>{text}</b>"

                        # Wrap in the determined tag with color style
                        #text_with_tag = f"<{tag_for_text} style='color:{font_color};'>{text}</{tag_for_text}>\n"
                        block_text.append(text)

            # Join all block text without additional wrapping since `tag_for_text` handles it
            #rows_with_html.append((page_num, block_id, ' '.join(block_text), ' '.join(original_text)))
            rows_with_html.append((page_num, block_id, f"<{tag_for_text}>{' '.join(block_text)}</{tag_for_text}>", ' '.join(original_text)))

    # Create the final DataFrame
    grouped_df = pd.DataFrame(rows_with_html, columns=['page_num', 'block_id', 'text', 'originalText'])
    return grouped_df
