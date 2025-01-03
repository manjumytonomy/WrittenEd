import os
import shutil
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(filename='files_converted.log', 
                    level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def sync_folders(old_package, new_package):
    """
    Synchronize files from old_package to new_package by copying files.
    
    Parameters:
        old_package (str): The path to the old package directory.
        new_package (str): The path to the new package directory.
    """
    file_copied_count = defaultdict(int)  # Dictionary to keep track of copied files per directory
    
    for root, dirs, files in os.walk(old_package):
        # Compute the relative path from the old_package root
        rel_path = os.path.relpath(root, old_package)
        new_root = os.path.join(new_package, rel_path)
        
        # Create corresponding directories in new_package
        if not os.path.exists(new_root):
            os.makedirs(new_root)
        
        for file in files:
            old_file_path = os.path.join(root, file)
            new_file_path = os.path.join(new_root, file)
            
            # Copy the file from old_package to new_package only if it does not exist
            if not os.path.exists(new_file_path):
                shutil.copy2(old_file_path, new_file_path)  # Use copy2 to copy with metadata
                file_copied_count[new_root] += 1
                print(f"Copied: {old_file_path} -> {new_file_path}")
    
    # Log the summary of files copied per directory
    logging.info("Summary of files copied per directory:")
    for folder, count in file_copied_count.items():
        logging.info(f"{folder.replace(new_package, '')}: {count} files copied")

if __name__ == "__main__":
    # Absolute paths to the old and new package directories
    old_package = '/Users/viveknarayana/Desktop/Archive'
    new_package = '/Users/viveknarayana/Desktop/Archive Copy'
    
    sync_folders(old_package, new_package)
