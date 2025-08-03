import rdflib
import yaml
import os
import re
from urllib.parse import urlparse

def sanitize_filename(text):
    """
    Sanitizes a string to be a valid, URL-friendly filename.
    """
    # Replace spaces and other characters with underscores
    sanitized = re.sub(r'[\s",?#\[\]\(\)\+\'/]', '_', text)
    # Remove any other non-alphanumeric characters, except for underscores and hyphens
    sanitized = re.sub(r'[^\w\s-]', '', sanitized).strip().lower()
    # Replace multiple underscores with a single one
    sanitized = re.sub(r'[-_]+', '_', sanitized)
    return sanitized.strip('_')

def get_uri_last_part(uri: str) -> str:
    """
    Helper function to robustly extract the last part of a URI,
    handling both standard URIs and common prefixed identifiers.
    """
    if ':' in uri and not uri.startswith('http'):
        return uri.split(':', 1)[1]
    
    try:
        parsed_uri = urlparse(uri)
        if parsed_uri.fragment:
            return parsed_uri.fragment
        
        path_parts = parsed_uri.path.split('/')
        label = next((part for part in reversed(path_parts) if part), '')
        if label:
            return label
    except Exception:
        pass

    return uri


def convert_ttl_to_individual_markdown(input_ttl_path, output_dir_path):
    """
    Reads an RDF Turtle file, identifies skos:Collection entities, and
    generates an individual Markdown file for each collection.

    Args:
        input_ttl_path (str): The path to the input Turtle (.ttl) file.
        output_dir_path (str): The path to the output directory where Markdown files will be saved.
    """
    if not os.path.exists(input_ttl_path):
        print(f"Error: The input file '{input_ttl_path}' was not found.")
        return

    os.makedirs(output_dir_path, exist_ok=True)
    print(f"Output directory '{output_dir_path}' ensured.")

    g = rdflib.Graph()
    try:
        g.parse(input_ttl_path, format="turtle")
        print(f"Successfully parsed graph with {len(g)} triples.")
    except Exception as e:
        print(f"Error parsing Turtle file: {e}")
        return

    skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

    query_collections = """
    SELECT ?collection WHERE {
        ?collection a skos:Collection .
    }
    """
    collections = [row.collection for row in g.query(query_collections)]

    if not collections:
        print("No skos:Collection entities were found in the graph.")
        return

    print(f"Found {len(collections)} skos:Collection entities. Creating individual files...")

    for collection_uri in collections:
        collection_data = {
            "uri": str(collection_uri),
            "aliases": None,
            "members": []
        }

        label = g.value(subject=collection_uri, predicate=skos.prefLabel)
        if label:
            collection_data["aliases"] = str(label)
        
        members = g.objects(subject=collection_uri, predicate=skos.member)
        for member_uri in members:
            # Format the member label with brackets and quotes for the YAML
            formatted_member = f"[[{get_uri_last_part(str(member_uri))}]]"
            collection_data["members"].append(formatted_member)
        
        if collection_data["aliases"]:
            filename = sanitize_filename(collection_data["aliases"]) + ".md"
        else:
            filename = sanitize_filename(get_uri_last_part(str(collection_uri))) + ".md"
        
        output_file_path = os.path.join(output_dir_path, filename)

        with open(output_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write("---\n")
            # yaml.safe_dump automatically handles the outer quotes
            yaml.safe_dump(collection_data, md_file, sort_keys=False)
            md_file.write("---\n\n")
            md_file.write(f"# {collection_data.get('aliases', 'Untitled Collection')}\n\n")
            # The body is now cleaner as the list is in the front matter
            md_file.write("This document represents a collection of thesaurus concepts.\n")
            

    print(f"Successfully created {len(collections)} markdown files in '{output_dir_path}'.")

# --- Main Execution ---
if __name__ == "__main__":
    input_ttl = "/home/hide/Documents/Heidi2workspace/ttl_publish/gc_thesaurus.ttl"
    output_dir = "/home/hide/Documents/Heidi2workspace/heidi2/collections"

    convert_ttl_to_individual_markdown(input_ttl, output_dir)