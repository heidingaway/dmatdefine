import rdflib
import yaml
import os
import re
from urllib.parse import urlparse
from rdflib import URIRef # Import URIRef to convert string URIs to rdflib objects

# ==============================================================================
# SCRIPT CONFIGURATION BLOCK
# Change these variables to configure the script's input and output paths,
# the SPARQL query, and the predicates used for entity properties.
# ==============================================================================

# The path to the input Turtle (.ttl) file.
# Example: "path/to/your/knowledge_graph.ttl"
INPUT_TTL_PATH = "/home/hide/quartz/heidi2/ttl_publish/gc_thesaurus.ttl"

# The path to the output directory where Markdown files will be saved.
# The directory will be created if it does not exist.
# Example: "path/to/your/markdown_output"
OUTPUT_DIR_PATH = "/home/hide/quartz/heidi2/collections"

# The SPARQL query to select the target entities to convert to Markdown.
# The selected variable MUST be named '?entity'.
# Example for skos:Collection: "SELECT ?entity WHERE { ?entity a skos:Collection . }"
# Example for skos:Concept: "SELECT ?entity WHERE { ?entity a skos:Concept . }"
# Example for foaf:Person: "SELECT ?entity WHERE { ?entity a foaf:Person . }"
SPARQL_QUERY_TARGET_ENTITIES = """
SELECT ?entity WHERE {
    ?entity a skos:Collection .
}
"""

# The URI of the predicate to use for the main label of the entity.
# This will be used for the Markdown filename and the 'aliases' in front matter.
# Example for SKOS: "http://www.w3.org/2004/02/skos/core#prefLabel"
# Example for FOAF: "http://xmlns.com/foaf/0.1/name"
ENTITY_LABEL_PREDICATE_URI = "http://www.w3.org/2004/02/skos/core#prefLabel"

# The URI of the predicate to use for "narrower" or related entities.
# These will be listed under 'narrower' in the front matter.
# Example for SKOS: "http://www.w3.org/2004/02/skos/core#narrower"
# Example for FOAF: "http://xmlns.com/foaf/0.1/knows"
ENTITY_RELATION_PREDICATE_URI = "http://www.w3.org/2004/02/skos/core#narrower"


# ==============================================================================
# END OF CONFIGURATION BLOCK
# ==============================================================================


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


def convert_ttl_to_individual_markdown(input_ttl_path, output_dir_path, sparql_query, 
                                      label_predicate_uri, relation_predicate_uri):
    """
    Reads an RDF Turtle file, identifies target entities using a provided
    SPARQL query, and generates an individual Markdown file for each entity.

    Args:
        input_ttl_path (str): The path to the input Turtle (.ttl) file.
        output_dir_path (str): The path to the output directory where Markdown files will be saved.
        sparql_query (str): The SPARQL query string to identify target entities.
        label_predicate_uri (str): The URI string for the predicate used as the entity's main label.
        relation_predicate_uri (str): The URI string for the predicate used for related entities (e.g., narrower).
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

    # Convert predicate URI strings to rdflib.URIRef objects
    label_predicate = URIRef(label_predicate_uri)
    relation_predicate = URIRef(relation_predicate_uri)
    
    # Execute the configurable SPARQL query.
    # The query must select a variable named '?entity'.
    entities_to_process = [row.entity for row in g.query(sparql_query)]

    if not entities_to_process:
        print("No entities were found in the graph based on the provided SPARQL query.")
        return

    print(f"Found {len(entities_to_process)} entities. Creating individual files...")

    for entity_uri in entities_to_process:
        entity_data = {
            "uri": str(entity_uri),
            "context": "gct", # This 'context' might need to be configurable or dynamic based on use case
            "aliases": None,
            "relationships": [] # Renamed from 'narrower' to be more general
        }

        # Get the label using the configurable predicate
        label = g.value(subject=entity_uri, predicate=label_predicate)
        if label:
            entity_data["aliases"] = str(label)
        
        # Get related entities using the configurable predicate
        related_entities = g.objects(subject=entity_uri, predicate=relation_predicate)
        for related_uri in related_entities:
            # Format the member label with brackets and quotes for the YAML
            formatted_member = f"[[{get_uri_last_part(str(related_uri))}]]"
            entity_data["relationships"].append(formatted_member) # Use 'relationships' key
        
        # Determine filename based on alias or URI last part
        if entity_data["aliases"]:
            filename = sanitize_filename(entity_data["aliases"]) + ".md"
        else:
            filename = sanitize_filename(get_uri_last_part(str(entity_uri))) + ".md"
        
        output_file_path = os.path.join(output_dir_path, filename)

        with open(output_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write("---\n")
            yaml.safe_dump(entity_data, md_file, sort_keys=False)
            md_file.write("---\n\n")
            # Use a more general title for the Markdown file
            md_file.write(f"# {entity_data.get('aliases', 'Untitled Entity')}\n\n")
            md_file.write("This document represents a knowledge graph entity.\n")
            

    print(f"Successfully created {len(entities_to_process)} markdown files in '{output_dir_path}'.")

# --- Main Execution ---
if __name__ == "__main__":
    convert_ttl_to_individual_markdown(
        INPUT_TTL_PATH, 
        OUTPUT_DIR_PATH, 
        SPARQL_QUERY_TARGET_ENTITIES,
        ENTITY_LABEL_PREDICATE_URI,
        ENTITY_RELATION_PREDICATE_URI
    )