import requests
import os
from typing import Any

def download_file_from_url(url: str, file_path: str, headers: dict[str, Any] = None) -> bool:
    """
    Downloads content from a URL to a local file, using customizable headers.

    Args:
        url (str): The URL of the resource to download.
        file_path (str): The local path to save the fil. Make sure to enter the correct extension for the content.
        headers (dict[str, Any], optional): A dictionary of headers to use for the request.
                                            Defaults to a generic browser-like set.

    Returns:
        bool: True if the download was successful, False otherwise.
    """
    if headers is None:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
        }
        print("Using default browser headers.")
    else:
        print("Using provided headers.")
        
    try:
        print(f"Attempting to download file from: {url}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        if response.history:
            print(f"\nWarning: The request was redirected from {response.history[0].url} to {response.url}")

        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"\nSuccessfully downloaded content to '{file_path}'")
        return True

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during download: {e}")
        return False