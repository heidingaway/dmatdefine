import pandas as pd
import os 
import re

invalid_chars_pattern = r'[<>:"/\\|?*& ]'

def create_empty_markdown_files(item_list, output_directory="empty_markdown_files"):
    """
    Creates empty Markdown files with cleaned filenames based on an input list of strings,
    using an externally defined invalid filename pattern.

    Args:
        item_list (list): A list of strings. Each string will be used to generate
                          a filename for a new, empty Markdown file.
        output_directory (str): The directory where the Markdown files will be saved.
    """

    # Create the output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    # print(f"Ensuring output directory exists: {output_directory}") # Optional: keep for debugging

    for i, item in enumerate(item_list):
        # 1. Generate a clean filename from the list item
        # Use the externally defined pattern for replacement
        cleaned_name = re.sub(invalid_filename_segment_pattern, "_", item)

        # Remove leading/trailing underscores if any were introduced
        cleaned_name = cleaned_name.strip('_')

        # Handle cases where cleaning results in an empty string
        if not cleaned_name:
            cleaned_name = f"untitled_document_{i+1}"

        # Construct the full filename with .md extension
        base_file_name = f"{cleaned_name}.md"
        file_path = os.path.join(output_directory, base_file_name)

        try:
            # Open in write mode ('w'). If content is empty, it creates an empty file.
            with open(file_path, 'w', encoding='utf-8') as f:
                # No f.write() call means the file will be empty
                pass
            # print(f"Successfully created empty file: {file_path}") # Optional: keep for debugging
        except IOError as e:
            # print(f"Error creating file {file_path}: {e}") # Optional: keep for debugging
            pass # Or handle specific error logging externally
        except Exception as e:
            # print(f"An unexpected error occurred for {file_path}: {e}") # Optional: keep for debugging
            pass # Or handle specific error logging externally