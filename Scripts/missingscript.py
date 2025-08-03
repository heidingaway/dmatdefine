import os
import shutil

def synchronize_directories(source_dir, destination_dir):
    """
    Synchronizes files from a source directory to a destination directory.
    - Adds files missing in the destination.
    - Replaces files of the same name in the destination with those from the source.
    - Does NOT modify the source directory.

    Args:
        source_dir (str): The path to the source directory.
        destination_dir (str): The path to the destination directory.
    """
    if not os.path.isdir(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return
    
    # Create destination directory if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)
    print(f"Ensured destination directory '{destination_dir}' exists.")

    source_files = set(os.listdir(source_dir))
    destination_files = set(os.listdir(destination_dir))

    print(f"Found {len(source_files)} files in source: {source_dir}")
    print(f"Found {len(destination_files)} files in destination: {destination_dir}")

    files_to_copy = []
    files_to_replace = []

    for filename in source_files:
        source_file_path = os.path.join(source_dir, filename)
        destination_file_path = os.path.join(destination_dir, filename)

        if os.path.isfile(source_file_path): # Ensure it's a file, not a subdirectory
            if filename not in destination_files:
                files_to_copy.append((source_file_path, destination_file_path))
            else:
                # For simplicity, we always replace if the name matches.
                # For more advanced sync, you might compare timestamps or hashes.
                files_to_replace.append((source_file_path, destination_file_path))
        else:
            print(f"Skipping '{filename}' in source as it is not a file.")

    print("\n--- Starting Synchronization ---")

    # Copy missing files
    for src, dst in files_to_copy:
        try:
            shutil.copy2(src, dst) # copy2 preserves metadata
            print(f"Added: '{os.path.basename(src)}' to '{destination_dir}'")
        except Exception as e:
            print(f"Error adding '{os.path.basename(src)}': {e}")

    # Replace existing files
    for src, dst in files_to_replace:
        try:
            shutil.copy2(src, dst) # copy2 will overwrite existing files
            print(f"Replaced: '{os.path.basename(src)}' in '{destination_dir}'")
        except Exception as e:
            print(f"Error replacing '{os.path.basename(src)}': {e}")

    print("\n--- Synchronization Complete ---")

# --- Main Execution ---
if __name__ == "__main__":
    # Define your source and destination directories here
    # Example paths (replace with your actual paths):
    source_directory = "/home/hide/Documents/Heidi2workspace/script"
    destination_directory = "/home/hide/Documents/dmatdefine/Scripts"

    synchronize_directories(source_directory, destination_directory)