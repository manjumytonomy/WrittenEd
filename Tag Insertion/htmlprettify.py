from lxml import etree, html
import os

def format_element(element, level=0):
    indent = "    " * level
    
    if len(element):
        if element.text:
            element.text = f"\n{indent}    {element.text}"
        else:
            element.text = f"\n{indent}    "
        for child in element:
            format_element(child, level + 1)
        child.tail = f"\n{indent}"
    else:
        if element.text:
            element.text = f"{element.text}"
        if element.tail:
            element.tail = f"\n{indent}"
    
    if level > 0 and element.tail:
        element.tail = f"\n{indent}"
    
    if element.tag == 'head':
        for child in element:
            child.tail = f"\n{indent}    "
        if element[-1].tail:
            element[-1].tail = f"\n{indent}"
    
    # Ensure body tag is indented properly
    if element.tag == 'html':
        for child in element:
            if child.tag == 'head':
                child.tail = f"\n{indent}    "
            if child.tag == 'body':
                child.tail = f"\n{indent}    "
        element.tail = "\n"
    
    # Ensure div class="page" starts on a new line
    if element.tag == 'div' and 'class' in element.attrib and element.attrib['class'] == 'page':
        element.tail = f"\n{indent}"

    # Ensure <a> tag within <div> stays on the same line
    if element.tag == 'div' and any(child.tag == 'a' for child in element):
        for child in element:
            if child.tag == 'a':
                if element.text:
                    element.text = f"{element.text.strip()}"
                    print(f'element text: {element.text}')
                child.tail = None
    
    # Ensure <img> tags are on separate lines
    if element.tag == 'img':
        element.tail = f"\n{indent}"

def remove_duplicate_attributes(element):
    """Remove duplicate attributes from an element."""
    attribs = element.attrib
    unique_attribs = {}
    for key, value in attribs.items():
        if key not in unique_attribs:
            unique_attribs[key] = value
    element.attrib.clear()
    for key, value in unique_attribs.items():
        element.set(key, value)

def format_html_file(input_path, output_path):
    parser = html.HTMLParser(remove_blank_text=True)
    tree = html.parse(input_path, parser)
    root = tree.getroot()

    # Remove duplicate attributes from the <html> tag
    if root.tag == 'html':
        remove_duplicate_attributes(root)


    format_element(root)

    # Ensure the closing html tag is not indented
    root.tail = "\n"

    with open(output_path, 'wb') as file:
        tree.write(file, pretty_print=False, encoding='utf-8')
    
    # Read the output file and adjust the closing html tag indentation
    with open(output_path, 'r') as file:
        lines = file.readlines()

    # Fix the indentation of the closing </html> tag
    for i in range(len(lines)):
        if lines[i].strip() == "</html>":
            lines[i] = "</html>\n"

    with open(output_path, 'w') as file:
        file.writelines(lines)

def process_single_html_file(input_file, output_file):
    try:
        print(f"Input file path: {input_file}")
        print(f"Output file path: {output_file}")
        if not os.path.exists(input_file):
            print(f"Error: Input file does not exist.")
            return
        format_html_file(input_file, output_file)
        print(f"Formatted HTML file saved to {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

