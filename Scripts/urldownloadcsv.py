import requests

def download_csv(url, output_path):
    """
    Downloads a CSV file from a given URL and saves it to a specified path.

    Args:
        url (str): The URL of the CSV file to download.
        output_path (str): The local path to save the downloaded file.

    Returns:
        bool: True if the download was successful, False otherwise.
    """
    try:
        print(f"Downloading CSV from: {url}")
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"Successfully downloaded and saved the CSV to: {output_path}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the download: {e}")
        return False
    except IOError as e:
        print(f"An error occurred while writing to the file: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    csv_url = "https://canada.multites.net/cst/EAEAD1E6-7DD2-4997-BE7F-40BFB1CBE8A2/CST20250610.csv"
    output_filename = "CST20250610.csv"

    download_csv(csv_url, output_filename)