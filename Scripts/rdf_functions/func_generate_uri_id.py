import unicodedata
import re

def generate_uri_id(text: str) -> str:
    """
    Generates a URI-safe string by converting text to lowercase, normalizing
    Unicode characters, and replacing special characters.

    Args:
        text (str): The input string to be converted.

    Returns:
        str: A URI-safe string.
    """
    # 1. Normalize and clean the text in a single, chained operation.
    #    Handles conversion to string, lowercase, and Unicode normalization.
    sanitized_text = unicodedata.normalize('NFKD', str(text).lower()).encode('ascii', 'ignore').decode('utf-8')
    
    # 2. Use a single, more efficient regex to replace all unwanted characters
    #    with a single underscore and collapse multiple underscores.
    #    The regex pattern `[..._]+` matches one or more of the specified characters.
    uri_id = re.sub(r'[\s",?#\[\]\(\)\+\'/-]+', '_', sanitized_text)
    
    # 3. Clean up leading and trailing underscores.
    return uri_id.strip('_')