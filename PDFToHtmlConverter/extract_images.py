import fitz
from PIL import Image, ImageChops
import os 
import io
import configparser
import logging
import sys



config = configparser.ConfigParser()
config.read('../config.ini')

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

customer = config['CUSTOMER']['customer_name']
configCustomer = configparser.ConfigParser()
configCustomer.read(f'../CustomerConfigs/{customer}_config.ini')

# Set up logging
log_file = os.path.join(project_dir, config['LOGGING']['log_file'])
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

'''This python file handles the image extraction from a given PDF file. It extracts the bounding box of the image, separates 
the layers of the image and remove the background layers for transparent images.'''


def get_path_after_images(file_path):
    # Define the directory name
    directory_name = 'Images/'

    # Find the starting index of the portion after 'Images/'
    start_index = file_path.find(directory_name)

    if start_index == -1:
        raise ValueError(f"'{directory_name}' not found in the path")

    # Calculate the start index after 'Images/'
    start_index += len(directory_name)

    # Extract and return the portion after 'Images/'
    return file_path[start_index:]


# checks tuple range
def is_within_range(coord1, coord2, range_tolerance):
    return all(
        abs(c1 - c2) <= range_tolerance
        for c1, c2 in zip(coord1, coord2)
    )

def is_left_aligned(x1, page_width, alignment_threshold=100):
    if page_width - x1 < 100:
        return False
    return True

def extract_images_and_coordinates(pdf_path, page_number, scale):
    
    try:
        logging.info("EXTRACT IMAGE FUNCTION")
        print(f'extracting images for filepath: {pdf_path}')
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[page_number]
        output_image_dir = os.path.join(configCustomer[f'{customer}']['local_folder_path'], 'Folder Storage/HTML/Images')
        reference_image_dir = '../Images'
        images_info = []
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        page_width = page.rect.width 
        alignment = "left"

        logo_scaled_coords = (0.400001525878906, 0.949974060058594, 180.39999389648438, 33.3499755859375)
        
        # Load the logo image and add it to images_info if page_number is 1 and img_index is 1
        start_index = pdf_path.find('DownloadedPDFs')
        if start_index != -1:
            start_index += len('DownloadedPDFs')
            path_segment = pdf_path[start_index:]

            count_slashes = path_segment.count('/')
        prepend = ""
        for i in range(count_slashes-2):
            prepend += "../"
        if page_number == 0:
            logo_image_reference_filename = f"{prepend}../Images/{configCustomer[f'{customer}']['logo']}"
        
            logging.info(f'LOGO ADDED')
            images_info.append((logo_image_reference_filename, logo_scaled_coords, True, "left"))  # Add a flag to indicate it's the logo
        
        for img_index, img in enumerate(page.get_images(full=True)):
            print(f'img index: {img_index}')
            xref = img[0]  
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            img_rect = page.get_image_rects(xref)[0]
            coords = (img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1)

            # Open the main image
            logging.info("Before opening main image")
            image = Image.open(io.BytesIO(image_bytes))
            logging.info("Opened main image")
            # Check if there is a separate soft mask (alpha mask)
            if "smask" in base_image:
                smask_xref = base_image["smask"]
                logging.info("SMASK")
                try:
                    smask_image = pdf_document.extract_image(smask_xref)
                    alpha_mask_bytes = smask_image["image"]
                    alpha_mask_image = Image.open(io.BytesIO(alpha_mask_bytes)).convert("L")
                    if image.size == alpha_mask_image.size:
                        image = image.convert("RGBA")
                        image.putalpha(alpha_mask_image)
                except ValueError:
                    pass

            if image.mode == "RGBA":
                logging.info("RGBA")
                background = Image.new("RGBA", image.size, (255, 255, 255, 255))
                background.paste(image, (0, 0), image)
                image = background.convert("RGB")

            if image.mode == "CMYK":
                logging.info("CMYK")
                image = image.convert("RGB")

            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            image = image.resize((new_width, new_height))

            scaled_coords = (
                img_rect.x0 * scale,
                img_rect.y0 * scale,
                img_rect.x1 * scale,
                img_rect.y1 * scale
            )
            
            pdf_name = pdf_name.replace(" ", "").replace('"','').replace("'","").replace('&',' and ').replace(':','_').replace('’','') 
            image_save_filename = f"{output_image_dir}/{pdf_name}_page{page_number+1}_img{img_index+1}.png"
            # Calculates location of image reference with regards to file depth
            start_index = pdf_path.find('DownloadedPDFs')
            if start_index != -1:
                start_index += len('DownloadedPDFs')
                path_segment = pdf_path[start_index:]

                count_slashes = path_segment.count('/')
            prepend = ""
            for i in range(count_slashes-2):
                prepend += "../"
            image_reference_filename = f"{prepend}{reference_image_dir}/{pdf_name}_page{page_number+1}_img{img_index+1}.png"

            image.save(image_save_filename, format="PNG")
            logging.info(f' Image filename: {image_save_filename} in filepath: {pdf_name}')
            logging.info(f' The bounding box size is: {scaled_coords}')

            bottom_right_x = coords[2]
            if not is_left_aligned(bottom_right_x, page_width):
                alignment = "right"

            images_info.append((image_reference_filename, scaled_coords, False, alignment))  # Add a flag to indicate it's not the logo

        pdf_document.close()
        
        images_info_filtered = [item for item in images_info if not item[2]]
        
        # Check if images_info_filtered is not empty
        if not images_info_filtered:
            print("No images to process after filtering.")
            logging.error("No images to process after filtering.")
            return images_info
    

        '''
        The following code accounts for logos not being picked up as the img1, and if we need to delete all embedded mytonomy logo we can do so using this code.
        '''
        if configCustomer[f'{customer}'].getboolean('embed_customer_logo'):
            try:
                # Find the image with the smallest y-coordinate (highest position)
                min_y_image = min(images_info_filtered, key=lambda item: item[1][1])
                
                # Ensure min_y_image is a tuple of (filename, coordinates, flag, alignment)
                if len(min_y_image) != 4:
                    print(f"Unexpected data structure for min_y_image: {min_y_image}")
                    logging.error(f"Unexpected data structure for min_y_image: {min_y_image}")
                    return images_info

                min_y_filename, _, _, _ = min_y_image
            except ValueError as e:
                print(f"Error finding minimum y-coordinate: {e}")
                logging.error(f"Error finding minimum y-coordinate: {e}")
                return images_info

            # Get the filename for img1
            img1_filename_list = [item[0] for item in images_info if 'img1' in item[0]]
            #print(f'img1 filename: {img1_filename_list}')
            
            if img1_filename_list:
                img1_filename = img1_filename_list[0]
                # Swap the filenames
                if min_y_filename != img1_filename:
                    print(f'Minimum y coordinate file name not equal to first file')
                    try:
                        temp_path = os.path.join(output_image_dir, 'temp')

                        # Perform the file renaming operations
                        os.rename(os.path.join(output_image_dir, get_path_after_images(img1_filename)), temp_path)
                        os.rename(os.path.join(output_image_dir, get_path_after_images(min_y_filename)), os.path.join(output_image_dir, get_path_after_images(img1_filename)))
                        os.rename(temp_path, os.path.join(output_image_dir, get_path_after_images(min_y_filename)))
                    
                        
                    except Exception as e:
                        print(f'error in swapping image names: {e}')
                        logging.error(f'error in swapping image names: {e}')
                    
                    # Update the list with the new filenames
                    updated_images_info = []
                    try:
                        for filename, coords, flag, alignment in images_info:
                            if filename == min_y_filename:
                                updated_images_info.append((img1_filename, coords, flag, alignment))
                            elif filename == img1_filename:
                                updated_images_info.append((min_y_filename, coords, flag, alignment))
                            else:
                                updated_images_info.append((filename, coords, flag, alignment))
                    except Exception as e:
                        logging.error(f"Error updating image info: {e}")
                        print(f'error in updating image info: {e}')
                        raise

                    images_info = updated_images_info
            images_info = [item for item in images_info if 'img1' not in item[0] or qr_code_check(item[1])]

        return images_info
    except Exception as e:
        logging.error(f"Error detected in extracting images and coordinates: {e}")
        sys.exit(1)
        
#function to ensure that QR Code is not removed even if it is a first image in the page
#This is to address the normal removal of first images in legacy 1 pager pdf or other legacy pdfs 
#However in the new template we have situations where QR Code would be the first image in subsequent pages or the last page. We dont want the QR Code in such situations
#to be removed
def qr_code_check(bbox):
    x0, y0, x1, y1 = bbox
    width = x1-x0
    height = y1-y0
    tolerance = 10
    logging.debug(height >= 60 and width >= height - tolerance and width <= height + tolerance)
    return height >= 60 and width >= height - tolerance and width <= height + tolerance

