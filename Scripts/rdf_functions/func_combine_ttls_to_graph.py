import os
from rdflib import Graph

def combine_ttls_to_graphs(file_paths: list[str]) -> Graph:
    """
    Parses a list of Turtle (.ttl) files into a single rdflib Graph.

    Args:
        file_paths (list[str]): A list of paths to the TTL files.

    Returns:
        Graph: A single rdflib Graph containing all parsed triples.
               Returns an empty Graph if no files are provided.
    """
    g = Graph()
    parsed_files_count = 0
    
    if not file_paths:
        print("No files to parse.")
        return g

    for file_path in file_paths:
        # A simple check to ensure the file has the correct extension
        if not file_path.lower().endswith('.ttl'):
            print(f"Skipping non-TTL file: {file_path}")
            continue
            
        try:
            g.parse(file_path, format="turtle")
            parsed_files_count += 1
            print(f"  Successfully parsed {os.path.basename(file_path)}. Triples: {len(g)}")
        except Exception as e:
            print(f"  Error parsing {file_path}: {e}")
            
    print(f"\nFinished parsing {parsed_files_count} TTL files.")
    print(f"Total triples in the combined graph: {len(g)}")
    return g