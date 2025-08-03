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
    Reads an RDF Turtle file, identifies skos:Concept entities that are not collections,
    and generates an individual Markdown file for each.

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

    query_concepts = """
    SELECT ?concept WHERE {
        ?concept a skos:Concept .
        MINUS {
            ?concept a skos:Collection .
        }
    }
    """
    concepts = [row.concept for row in g.query(query_concepts)]

    if not concepts:
        print("No skos:Concept entities (that are not collections) were found in the graph.")
        return

    print(f"Found {len(concepts)} skos:Concept entities. Creating individual files...")

    for concept_uri in concepts:
        concept_data = {
            "uri": str(concept_uri),
            "aliases": [],
            "broader": [],
            "narrower": [],
            "related": [],
            "altLabels": [],
            "scopeNote": []
        }

        # Get all prefLabels (aliases)
        for label in g.objects(subject=concept_uri, predicate=skos.prefLabel):
            concept_data["aliases"].append(str(label))

        # Get Broader Concepts
        for broader_uri in g.objects(subject=concept_uri, predicate=skos.broader):
            formatted_uri = f"[[{get_uri_last_part(str(broader_uri))}]]"
            concept_data["broader"].append(formatted_uri)

        # Get Narrower Concepts
        for narrower_uri in g.objects(subject=concept_uri, predicate=skos.narrower):
            formatted_uri = f"[[{get_uri_last_part(str(narrower_uri))}]]"
            concept_data["narrower"].append(formatted_uri)

        # Get Related Concepts
        for related_uri in g.objects(subject=concept_uri, predicate=skos.related):
            formatted_uri = f"[[{get_uri_last_part(str(related_uri))}]]"
            concept_data["related"].append(formatted_uri)

        # Get AltLabels
        for alt_label in g.objects(subject=concept_uri, predicate=skos.altLabel):
            concept_data["altLabels"].append(str(alt_label))

        # Get ScopeNote
        for note in g.objects(subject=concept_uri, predicate=skos.scopeNote):
            concept_data["scopeNote"].append(str(note))

        # Determine the output filename based on aliases
        if concept_data["aliases"]:
            # Use the English prefLabel for the filename if available
            en_label = next((l for l in concept_data["aliases"] if l.endswith('@en')), None)
            filename = sanitize_filename(en_label.replace('@en', '').strip()) + ".md" if en_label else sanitize_filename(concept_data["aliases"][0].replace('@fr', '').strip()) + ".md"
        else:
            filename = sanitize_filename(get_uri_last_part(str(concept_uri))) + ".md"
        
        output_file_path = os.path.join(output_dir_path, filename)

        with open(output_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write("---\n")
            yaml.safe_dump(concept_data, md_file, sort_keys=False)
            md_file.write("---\n\n")


    print(f"Successfully created {len(concepts)} markdown files in '{output_dir_path}'.")

# --- Main Execution ---
if __name__ == "__main__":
    input_ttl = "/home/hide/Documents/Heidi2workspace/ttl_publish/gc_thesaurus.ttl"
    output_dir = "/home/hide/Documents/Heidi2workspace/heidi2/concepts"

    convert_ttl_to_individual_markdown(input_ttl, output_dir)