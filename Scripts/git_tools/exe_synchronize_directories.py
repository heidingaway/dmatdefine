import os
import shutil

def synchronize_directories(source_dir, destination_dir):
    """
    Synchronizes a source directory and its entire contents (files and subdirectories)
    to a destination directory.

    - Adds missing files and directories to the destination.
    - Replaces files and directories of the same name in the destination.
    - Does NOT modify the source directory.

    Args:
        source_dir (str): The path to the source directory.
        destination_dir (str): The path to the destination directory.
    """
    if not os.path.isdir(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return

    print(f"Synchronizing from '{source_dir}' to '{destination_dir}'...")
    
    # Use os.walk to get a list of all files and directories in the source
    for root, dirs, files in os.walk(source_dir):
        # Calculate the relative path from the source directory
        relative_path = os.path.relpath(root, source_dir)
        
        # Construct the corresponding path in the destination directory
        destination_path = os.path.join(destination_dir, relative_path)
        
        # Create the destination directory if it doesn't exist
        os.makedirs(destination_path, exist_ok=True)
        
        # Iterate over files and copy them
        for filename in files:
            source_file_path = os.path.join(root, filename)
            destination_file_path = os.path.join(destination_path, filename)

            try:
                # copy2 preserves file metadata and overwrites existing files
                shutil.copy2(source_file_path, destination_file_path)
                print(f"  Copied file: '{os.path.join(relative_path, filename)}'")
            except Exception as e:
                print(f"  Error copying file '{source_file_path}': {e}")
                
    print("\n--- Synchronization Complete ---")

# --- Main Execution ---
if __name__ == "__main__":
    # Define your source and destination directories here
    source_directory = "/home/hide/Documents/Heidi2workspace/script"
    destination_directory = "/home/hide/Documents/dmatdefine/Scripts"

    synchronize_directories(source_directory, destination_directory)