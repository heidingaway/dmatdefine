import os

def find_by_extension(folder_path: str, file_extension: str = "") -> list[str]:
    """
    Finds files with a specific extension in a given folder.

    Args:
        folder_path (str): The path to the folder.
        file_extension (str): The file extension to search for, e.g., ".txt".
                              Defaults to an empty string to return all files.

    Returns:
        list[str]: A list of full paths to the matching files.
                   Returns an empty list if the folder is not found or is empty.
    """
    if not isinstance(folder_path, str) or not os.path.isdir(folder_path):
        print(f"Error: The provided folder path '{folder_path}' is not valid or does not exist.")
        return []

    file_paths = []
    for filename in os.listdir(folder_path):
        # The os.path.join() ensures cross-platform compatibility
        full_path = os.path.join(folder_path, filename)
        
        # Check if it's a file and not a directory
        if os.path.isfile(full_path):
            if file_extension == "" or filename.endswith(file_extension):
                file_paths.append(full_path)
    
    return file_paths