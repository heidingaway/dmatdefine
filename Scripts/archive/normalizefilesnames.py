import os
import re

# This is a slightly modified version of the previous normalization function
# that handles renaming with full paths.
def normalize_filename_for_renaming(filename: str) -> str:
    """
    Normalizes a filename for physical renaming.
    Converts to lowercase, removes the file extension, and replaces
    problematic characters with underscores.
    
    Args:
        filename (str): The original filename, e.g., "My File-Name.md".

    Returns:
        str: The normalized filename, e.g., "my_file_name.md".
    """
    if not filename.endswith(".md"):
        return filename
    
    name_without_ext = os.path.splitext(filename)[0]
    
    # Convert to lowercase
    normalized_name = name_without_ext.lower()
    
    # Replace spaces, hyphens, and other non-alphanumeric characters with underscores
    normalized_name = re.sub(r'[^a-zA-Z0-9_]', '_', normalized_name)
    
    return f"{normalized_name}.md"


def rename_files_in_directory(directory_path: str):
    """
    Walks through a directory and renames all .md files to be lowercase,
    with spaces and other characters replaced by underscores.

    Args:
        directory_path (str): The path to the directory to process.
    """
    print(f"Starting to rename Markdown files in '{directory_path}'...")
    renamed_count = 0
    
    for root, _, files in os.walk(directory_path):
        for filename in files:
            if filename.endswith(".md"):
                normalized_filename = normalize_filename_for_renaming(filename)

                if filename != normalized_filename:
                    old_path = os.path.join(root, filename)
                    new_path = os.path.join(root, normalized_filename)
                    
                    try:
                        os.rename(old_path, new_path)
                        print(f"  Renamed: '{filename}' -> '{normalized_filename}'")
                        renamed_count += 1
                    except OSError as e:
                        print(f"  Error renaming '{old_path}': {e}")
    
    print(f"\nFinished. Successfully renamed {renamed_count} files.")


# Uncomment and set your directory to use this function
RENAME_TARGET_DIR = "/home/hide/Documents/Heidi2workspace/heidi2/publish"
rename_files_in_directory(RENAME_TARGET_DIR)