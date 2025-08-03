import rdflib
import yaml
import os
import re

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

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir_path, exist_ok=True)
    print(f"Output directory '{output_dir_path}' ensured.")

    g = rdflib.Graph()
    try:
        g.parse(input_ttl_path, format="turtle")
        print(f"Successfully parsed graph with {len(g)} triples.")
    except Exception as e:
        print(f"Error parsing Turtle file: {e}")
        return

    # Identify all URIs that are declared as skos:Collection
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

        # Get the preferred label for the collection
        label = g.value(subject=collection_uri, predicate=rdflib.URIRef("http://www.w3.org/2004/02/skos/core#aliases"))
        if label:
            collection_data["aliases"] = str(label)
        
        # Get all members of the collection
        members = g.objects(subject=collection_uri, predicate=rdflib.URIRef("http://www.w3.org/2004/02/skos/core#member"))
        for member_uri in members:
            collection_data["members"].append(str(member_uri))
        
        # Determine the output filename
        if collection_data["aliases"]:
            filename = sanitize_filename(collection_data["aliases"]) + ".md"
        else:
            filename = sanitize_filename(str(collection_uri.split('/')[-1])) + ".md"
        
        output_file_path = os.path.join(output_dir_path, filename)

        # Write the Markdown file with YAML front matter
        with open(output_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write("---\n")
            yaml.safe_dump(collection_data, md_file, sort_keys=False)
            md_file.write("---\n\n")

    print(f"Successfully created {len(collections)} markdown files in '{output_dir_path}'.")

# --- Main Execution ---
if __name__ == "__main__":
    input_ttl = "/home/hide/Documents/Heidi2workspace/ttl_publish/gc_thesaurus.ttl"
    output_dir = "/home/hide/Documents/Heidi2workspace/heidi2/collections"

    convert_ttl_to_individual_markdown(input_ttl, output_dir)